// Attribution test (Gate 1) — the "python" stand-in: a SEPARATE child binary
// that does the actual read. Bare/adhoc on purpose (mimics uv's downloaded
// python: untrusted, not ours). READ-ONLY.

#include <dirent.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const char *home = getenv("HOME");
    char path[1024];
    snprintf(path, sizeof path,
             "%s/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus",
             home ? home : "");

    DIR *d = opendir(path);
    if (d) { printf("reader: opened OmniFocus container (granted)\n"); closedir(d); }
    else   { printf("reader: DENIED/missing\n"); }
    sleep(2);
    return 0;
}
