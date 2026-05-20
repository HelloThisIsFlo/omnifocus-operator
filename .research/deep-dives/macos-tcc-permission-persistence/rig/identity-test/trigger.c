// Identity test (Rounds A/B): a single binary that reads OmniFocus's container,
// triggering the macOS "access data from other apps" (SystemPolicyAppData) prompt.
// Adhoc build = Round A (control). Re-signed = Round B.
// READ-ONLY: lists a directory handle; no file contents, no writes, no DB access.

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
    if (d) { printf("OK: opened OmniFocus container (granted)\n"); closedir(d); }
    else   { printf("DENIED/missing\n"); }
    sleep(3);
    return 0;
}
