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
            // Client-side: use console
            const logFn = console[level] || console.log;
            if (meta) {
                logFn(`[${level.toUpperCase()}] ${message}`, meta);
            } else {
                logFn(`[${level.toUpperCase()}] ${message}`);
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
