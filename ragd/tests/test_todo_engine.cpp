#include "ragd/todo_engine.h"
#include <cassert>
int main() {
  ragd::TodoEngine e;
  auto todos = e.extract("a.cpp", "// SECURITY: fix auth\n// TODO: normal thing\n");
  assert(todos.size() == 2);
  assert(todos.front().priority == 1);
  return 0;
}
