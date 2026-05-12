#include "ragd/watcher.h"

#include <chrono>
#include <filesystem>
#include <iostream>
#include <unordered_map>
#include <vector>

#ifdef __linux__
#include <poll.h>
#include <sys/inotify.h>
#include <unistd.h>
#endif

namespace ragd {

namespace fs = std::filesystem;

Watcher::Watcher(Config config, Indexer &indexer) : config_(std::move(config)), indexer_(indexer) {}
Watcher::~Watcher() { stop(); }

void Watcher::start() {
  if (running_) return;
  running_ = true;
  worker_ = std::thread([this] {
#ifdef __linux__
    int fd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
    if (fd >= 0) {
      std::unordered_map<int, fs::path> watch_paths;
      auto add_watch = [&](const fs::path &dir) {
        int wd = inotify_add_watch(fd, dir.c_str(), IN_MODIFY | IN_CLOSE_WRITE | IN_CREATE | IN_DELETE | IN_MOVED_FROM | IN_MOVED_TO | IN_Q_OVERFLOW);
        if (wd >= 0) watch_paths[wd] = dir;
      };
      for (const auto &root : config_.index_paths) {
        fs::path p(root);
        if (!fs::exists(p)) continue;
        if (fs::is_directory(p)) {
          add_watch(p);
          for (auto it = fs::recursive_directory_iterator(p); it != fs::recursive_directory_iterator(); ++it) {
            if (indexer_.should_ignore(it->path())) {
              if (it->is_directory()) it.disable_recursion_pending();
              continue;
            }
            if (it->is_directory()) add_watch(it->path());
          }
        } else {
          add_watch(p.parent_path());
        }
      }

      std::unordered_map<std::string, std::chrono::steady_clock::time_point> pending;
      std::vector<char> buffer(64 * 1024);
      while (running_) {
        pollfd pfd{fd, POLLIN, 0};
        int rc = poll(&pfd, 1, 200);
        auto now = std::chrono::steady_clock::now();
        if (rc > 0 && (pfd.revents & POLLIN)) {
          ssize_t len = read(fd, buffer.data(), buffer.size());
          for (char *ptr = buffer.data(); len > 0 && ptr < buffer.data() + len;) {
            auto *ev = reinterpret_cast<inotify_event *>(ptr);
            auto base = watch_paths.count(ev->wd) ? watch_paths[ev->wd] : fs::path{};
            fs::path path = ev->len ? base / ev->name : base;
            if (ev->mask & IN_Q_OVERFLOW) {
              indexer_.index_paths(config_.index_paths, config_.max_file_bytes);
            } else if ((ev->mask & IN_ISDIR) && (ev->mask & (IN_CREATE | IN_MOVED_TO)) && fs::exists(path)) {
              add_watch(path);
            } else if (ev->mask & (IN_DELETE | IN_MOVED_FROM)) {
              indexer_.mark_deleted(path);
            } else if (!(ev->mask & IN_ISDIR) && (ev->mask & (IN_MODIFY | IN_CLOSE_WRITE | IN_CREATE | IN_MOVED_TO))) {
              pending[fs::absolute(path).string()] = now;
            }
            ptr += sizeof(inotify_event) + ev->len;
          }
        }

        for (auto it = pending.begin(); it != pending.end();) {
          if (std::chrono::duration_cast<std::chrono::milliseconds>(now - it->second).count() >= 300) {
            indexer_.index_file(it->first, config_.max_file_bytes);
            it = pending.erase(it);
          } else {
            ++it;
          }
        }
      }
      close(fd);
      return;
    }
    std::cerr << "ragd: inotify unavailable; falling back to polling watcher\n";
#endif
    while (running_) {
      indexer_.index_paths(config_.index_paths, config_.max_file_bytes);
      std::this_thread::sleep_for(std::chrono::seconds(10));
    }
  });
}

void Watcher::stop() {
  running_ = false;
  if (worker_.joinable()) worker_.join();
}

}  // namespace ragd
