/*
* Copyright (c) 2010 Red Hat, Inc.
*
* Authors: Jeff Ortel <jortel@redhat.com>
*
* This software is licensed to you under the GNU General Public License,
* version 2 (GPLv2). There is NO WARRANTY for this software, express or
* implied, including the implied warranties of MERCHANTABILITY or FITNESS
* FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
* along with this software; if not, see
* http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
*
* Red Hat trademarks are not licensed under GPLv2. No permission is
* granted to use or replicate Red Hat trademarks that are incorporated
* in this software or its documentation.
*/

#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <wait.h>

#define LOGFILE "/var/log/rhsm/rhsmcertd.log"

static FILE *log = 0;


void printUsage()
{
    printf("usage: rhsmcertd <interval>");
}

char *ts()
{
    time_t tm = time(0);
    char *ts = asctime(localtime(&tm));
    char *p = ts;
    while(*p)
    {
        p++;
        if(*p == '\n')
        {
           *p = 0;
        }
    }
    return ts;
}

int run(int interval)
{
    int status = 0;
    fprintf(log, "%s: started: interval = %d\n", ts(), interval);
    fflush(log);
    while(1)
    {
        int pid = fork();
        if(pid < 0)
        {
            fprintf(log, "%s: fork failed\n", ts());
            fflush(log);
            return 1;
        }
        if(pid == 0)
        {
            execl("/usr/bin/python", "python", "/usr/share/rhsm/certmgr.py", 0);
        }
        waitpid(pid, &status, 0);
        status = WEXITSTATUS(status);
        if(status == 0)
        {
            fprintf(log, "%s: certificates updated\n", ts());
            fflush(log);
            sleep(interval);
        }
        else
        {
            fprintf(log, "%s: update failed (%d)\n", ts(), status);
            fflush(log);
        }
    }

    return status;
}

int main(int argc, char *argv[])
{
    log = fopen(LOGFILE, "a+");
    if(log == 0) return 1;
    if(argc < 2)
    {
        printUsage();
        return 0;
    }
    int pid = fork();
    if(pid == 0)
    {
        daemon(0, 0);
        run(atoi(argv[1]));
    }
    fclose(log);
}
