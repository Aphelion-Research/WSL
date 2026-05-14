#include <string>

class Greeter {
public:
  std::string greet(const std::string& name) {
    return "hello " + name;
  }
};

int add(int a, int b) {
  return a + b;
}
