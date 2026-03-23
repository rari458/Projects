#include "../kernel/types.h"
#include "../kernel/stat.h"
#include "user.h"

int
main(int argc, char *argv[])
{
    printf("pid,state,name\n");

    if (argc == 1) {
        ps(0);
    } else {
        for (int i = 1; i < argc; i++) {
            int target_pid = atoi(argv[i]);
            ps(target_pid);
        }
    }

    exit(0);
}