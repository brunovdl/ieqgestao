/**
 * Utility functions to handle dates in the America/Sao_Paulo timezone.
 * This ensures consistency across the application regardless of the user's local time
 * or the server's UTC time.
 */

export function getBrasiliaDateString(date?: Date): string {
    const d = date || new Date();
    // Returns YYYY-MM-DD in America/Sao_Paulo timezone
    const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'America/Sao_Paulo',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
    return formatter.format(d);
}

export function getBrasiliaTimestampString(date?: Date): string {
    const d = date || new Date();
    // Returns ISO-like string with offset for America/Sao_Paulo e.g., "2023-10-25T15:30:00-03:00"
    const formatter = new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'America/Sao_Paulo',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    const svString = formatter.format(d); // format: "YYYY-MM-DD HH:mm:ss"
    return svString.replace(' ', 'T') + '-03:00';
}
