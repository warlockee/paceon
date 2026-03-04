/*
 * main.c - Orchestrator for paceon Telegram bot
 *
 * Contains global variable definitions and the main() entry point.
 * Reads like a recipe: parse args -> init TOTP -> start manager -> run bot.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <pthread.h>

#include "types.h"
#include "bot.h"
#include "state.h"
#include "commands.h"
#include "totp.h"
#include "terminal_io.h"
#include "manager_ipc.h"

/* ============================================================================
 * Global state (declared extern in types.h / used by other modules)
 * ========================================================================= */

TermInfo *TermList = NULL;
int TermCount = 0;
int Connected = 0;
char ConnectedId[128] = {0};
pid_t ConnectedPid = 0;
char ConnectedName[128] = {0};
char ConnectedTitle[256] = {0};
int DangerMode = 0;

/* Internal state shared across modules. */
pthread_mutex_t RequestLock = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t MgrLock = PTHREAD_MUTEX_INITIALIZER;
volatile sig_atomic_t ShutdownRequested = 0;
int WeakSecurity = 0;             /* If 1, skip all OTP logic. */
int Authenticated = 0;            /* Whether OTP has been verified. */
time_t LastActivity = 0;          /* Last time owner sent a valid command. */
int OtpTimeout = 300;             /* Timeout in seconds (default 5 min). */

int64_t TrackedMsgIds[MAX_TRACKED_MSGS];
int TrackedMsgCount = 0;

/* LLM Manager Agent (paceon-mgr) */
int MgrMode = 0;                  /* 1 if in manager conversation mode. */
pid_t MgrPid = -1;                /* PID of mgr child process. */
int MgrWriteFd = -1;              /* Pipe: paceon writes to mgr stdin. */
int MgrReadFd = -1;               /* Pipe: paceon reads mgr stdout. */
pthread_t MgrReaderThread;
int MgrReaderRunning = 0;
char MgrPath[512] = {0};          /* Path to paceon-mgr script. */

/* ============================================================================
 * Signal Handlers
 * ========================================================================= */

static void shutdown_handler(int sig) {
    (void)sig;
    ShutdownRequested = 1;
    if (MgrPid > 0) kill(MgrPid, SIGTERM);
}

/* ============================================================================
 * Main
 * ========================================================================= */

int main(int argc, char **argv) {
    setlinebuf(stdout);  /* Force line-buffered so log output appears in real time. */

    /* Parse our custom flags. */
    const char *dbfile = "./mybot.sqlite";
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--dangerously-attach-to-any-window") == 0) {
            DangerMode = 1;
            printf("DANGER MODE: All windows will be visible.\n");
        } else if (strcmp(argv[i], "--use-weak-security") == 0) {
            WeakSecurity = 1;
            printf("WARNING: OTP authentication disabled.\n");
        } else if (strcmp(argv[i], "--dbfile") == 0 && i+1 < argc) {
            dbfile = argv[i+1];
        } else if (strcmp(argv[i], "--mgr") == 0 && i+1 < argc) {
            strncpy(MgrPath, argv[i+1], sizeof(MgrPath) - 1);
            MgrPath[sizeof(MgrPath) - 1] = '\0';
            printf("MGR: Manager script: %s\n", MgrPath);
        }
    }

    /* Ignore SIGPIPE so writes to broken mgr pipe return EPIPE instead. */
    signal(SIGPIPE, SIG_IGN);

    /* Graceful shutdown on SIGTERM/SIGINT. */
    signal(SIGTERM, shutdown_handler);
    signal(SIGINT, shutdown_handler);

    /* TOTP setup: check/generate secret before starting the bot. */
    totp_setup(dbfile);

    /* Start manager eagerly so it's warm when the user first messages. */
    if (MgrPath[0] != '\0') {
        mgr_start();
    }

    /* Triggers: respond to all private messages. */
    static char *triggers[] = { "*", NULL };

    startBot(TB_CREATE_KV_STORE, argc, argv, TB_FLAGS_IGNORE_BAD_ARG,
             handle_request, cron_callback, triggers);
    return 0;
}
