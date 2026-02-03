import winston from 'winston';
import 'winston-daily-rotate-file';
import path from 'path';

// Define log directory (outside src source)
// In Docker, we usually map this volume
const LOG_DIR = path.join(process.cwd(), 'logs');

// Define log format
const logFormat = winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
        return `${timestamp} [${level.toUpperCase()}]: ${message} ${Object.keys(meta).length ? JSON.stringify(meta) : ''
            }`;
    })
);

// Create logger instance
const logger = winston.createLogger({
    level: process.env.NODE_ENV === 'development' ? 'debug' : 'info',
    format: winston.format.json(), // Base format for files is often JSON
    transports: [
        // 1. Console transport (for docker logs)
        new winston.transports.Console({
            format: winston.format.combine(
                winston.format.colorize(),
                logFormat
            ),
        }),
    ],
});

// Add file transports ONLY on the server side
if (typeof window === 'undefined') {
    // Daily rotate file for all logs
    logger.add(
        new winston.transports.DailyRotateFile({
            filename: path.join(LOG_DIR, 'app-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            zippedArchive: true,
            maxSize: '20m',
            maxFiles: '14d',
            format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
        })
    );

    // Separate file for errors
    logger.add(
        new winston.transports.DailyRotateFile({
            filename: path.join(LOG_DIR, 'error-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            zippedArchive: true,
            maxSize: '20m',
            maxFiles: '30d',
            level: 'error',
            format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
        })
    );
}

export default logger;
