#include "ragd/vector_store.h"
#include <cassert>
int main() {
  ragd::VectorStore v;
  v.add(1, "gold xauusd ticks");
  v.add(2, "unrelated apples");
  auto r = v.query("xauusd gold", 2);
  assert(!r.empty());
  assert(r.front().chunk_id == 1);
  return 0;
}
