import { TFunction } from 'i18next';

const MS_PER_DAY = 1000 * 60 * 60 * 24;

/**
 * Turns an ISO timestamp into a localised relative label. Works with the mock
 * data today and with backend timestamps later, without touching the screens.
 */
export function formatRelativeDate(isoDate: string, t: TFunction): string {
  const timestamp = new Date(isoDate).getTime();

  if (Number.isNaN(timestamp)) {
    return '';
  }

  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);

  const days = Math.max(0, Math.floor((startOfToday.getTime() - timestamp) / MS_PER_DAY) + 1);

  if (days <= 0) {
    return t('time.today');
  }

  if (days === 1) {
    return t('time.yesterday');
  }

  if (days < 7) {
    return t('time.daysAgo', { count: days });
  }

  const weeks = Math.floor(days / 7);

  return weeks === 1 ? t('time.oneWeekAgo') : t('time.weeksAgo', { count: weeks });
}
