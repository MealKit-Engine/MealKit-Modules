// Module unit tests: built against the engine core by tests/CMakeLists.txt (the shared module CI runs them).
#include "mymodule/sim/Counter.h"
#include "mymodule/view/CounterView.h"

#include <cstdio>

static int g_failed = 0;
#define CHECK(x)                                                                                                       \
    do {                                                                                                               \
        if (!(x)) {                                                                                                    \
            std::printf("%s(%d): FAIL %s\n", __FILE__, __LINE__, #x);                                                  \
            ++g_failed;                                                                                                \
        }                                                                                                              \
    } while (0)

int main() {
    mymodule::Counter c;
    c.limit = 2;
    CHECK(!mymodule::add(c));
    CHECK(mymodule::add(c));
    CHECK(!mymodule::add(c));
    CHECK(c.value == 2);
    CHECK(mymodule::fill(c) == 1.0f);

    if (g_failed) return 1;
    std::printf("mymodule tests: all passed\n");
    return 0;
}
