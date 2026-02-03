// Client-safe logger wrapper
// Uses winston on server, console on client

type LogLevel = 'info' | 'warn' | 'error' | 'debug';

class ClientSafeLogger {
    private serverLogger: any = null;

    constructor() {
        // Only import winston on server side
        if (typeof window === 'undefined') {
            try {
                // Dynamic import to avoid bundling on client
                const loggerModule = require('./logger');
                this.serverLogger = loggerModule.default;
            } catch (e) {
                console.error('Failed to load server logger:', e);
            }
        }
    }

    private log(level: LogLevel, message: string, meta?: any) {
        if (this.serverLogger) {
            // Server-side: use winston
            this.serverLogger[level](message, meta);
        } else {
            // Client-side: use console AND send to server
            const logFn = console[level] || console.log;
            if (meta) {
                logFn(`[${level.toUpperCase()}] ${message}`, meta);
            } else {
                logFn(`[${level.toUpperCase()}] ${message}`);
            }

            // Send to server for file storage (fire and forget)
            // We don't await this to avoid blocking UI
            // Only send info/warn/error to avoid spamming debug logs over network
            if (level !== 'debug') {
                console.log(`[ClientLogger] Attempting to send ${level} log to server...`);
                try {
                    fetch('/_ingest/logs', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            level,
                            message,
                            meta: {
                                ...meta,
                                url: window.location.href,
                                userAgent: navigator.userAgent
                            }
                        }),
                    })
                        .then(res => {
                            if (!res.ok) console.error(`[ClientLogger] Server responded with status: ${res.status}`);
                            else console.log('[ClientLogger] Log sent successfully');
                        })
                        .catch(err => console.error('[ClientLogger] Failed to send log to server:', err));
                } catch (e) {
                    // Ignore errors in logging to prevent loops
                }
            }
        }
    }

    info(message: string, meta?: any) {
        this.log('info', message, meta);
    }

    warn(message: string, meta?: any) {
        this.log('warn', message, meta);
    }

    error(message: string, meta?: any) {
        this.log('error', message, meta);
    }

    debug(message: string, meta?: any) {
        this.log('debug', message, meta);
    }
}

export default new ClientSafeLogger();
