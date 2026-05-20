// Attribution test (Gate 1) — the launcher (stands in for the signed app set as
// Claude's `command`). It does NOT touch OmniFocus; it SPAWNS the reader child,
// exactly as the real launcher would spawn uv -> python.
//
// Tests: when the CHILD reads, does macOS attribute the access to THIS launcher's
// identity (responsible process) or to the child?
//
// Usage: launcher <absolute-path-to-of-reader>
// (Run via Claude's disclaimer helper: disclaimer <launcher> <reader-path>)

#include <spawn.h>
#include <sys/wait.h>
#include <stdio.h>

extern char **environ;

int main(int argc, char **argv) {
    if (argc < 2) { printf("usage: launcher <reader-path>\n"); return 2; }
    char *reader = argv[1];
    char *args[] = { reader, NULL };

    printf("launcher: spawning reader child (%s)\n", reader);
    pid_t pid;
    if (posix_spawn(&pid, reader, NULL, NULL, args, environ) != 0) {
        printf("launcher: spawn failed\n");
        return 1;
    }
    int status;
    waitpid(pid, &status, 0);
    printf("launcher: reader exited\n");
    return 0;
}
