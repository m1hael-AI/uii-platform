'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect, Suspense } from 'react';
import logger from '@/lib/clientLogger';

function PageLoggerInner() {
    const pathname = usePathname();
    const searchParams = useSearchParams();

    useEffect(() => {
        const url = `${pathname}${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
        logger.info(`Page View: ${url}`, { pathname, searchParams: searchParams.toString() });
    }, [pathname, searchParams]);

    return null;
}

export default function PageLogger() {
    return (
        <Suspense fallback={null}>
            <PageLoggerInner />
        </Suspense>
    );
}
