import { NextRequest, NextResponse } from 'next/server';
import logger from '@/lib/logger';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { level, message, meta } = body;

        if (!level || !message) {
            return NextResponse.json(
                { error: 'Missing level or message' },
                { status: 400 }
            );
        }

        // Log using server-side winston logger
        // This will write to files defined in lib/logger.ts
        logger.log(level, message, meta);

        return NextResponse.json({ success: true });
    } catch (error) {
        console.error('Failed to process log:', error);
        return NextResponse.json(
            { error: 'Internal Server Error' },
            { status: 500 }
        );
    }
}
