// frontend/src/components/CookieConsent.tsx
'use client';

import { useEffect, useState } from 'react';
import * as CookieConsent from 'vanilla-cookieconsent';
import 'vanilla-cookieconsent/dist/cookieconsent.css';

interface CookieConsentProps {
  language?: string;
}

export default function CookieConsentBanner({ language = 'en' }: CookieConsentProps) {
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const initializeCookieConsent = async () => {
      try {
        // Fetch cookie consent configuration from API
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.bonidoc.com';
        const response = await fetch(`${apiUrl}/api/v1/settings/cookie-consent?language=${language}`);

        if (!response.ok) {
          console.error('Failed to fetch cookie consent config');
          return;
        }

        const config = await response.json();

        // Build categories configuration for vanilla-cookieconsent
        const categories: Record<string, { enabled: boolean; readOnly: boolean; autoClear?: { cookies: Array<{ name: RegExp | string }> } }> = {};
        const sections: Array<{ title: string; description: string; linkedCategory?: string; cookieTable?: { headers: Record<string, string>; body: Array<{ name: string; domain: string; desc: string; exp: string }> } }> = [
          {
            title: language === 'de'
              ? 'Cookie-Nutzung'
              : language === 'ru'
              ? 'Использование файлов cookie'
              : 'Cookie Usage',
            description: language === 'de'
              ? 'Wir verwenden Cookies, um die grundlegenden Funktionen der Website sicherzustellen und Ihre Online-Erfahrung zu verbessern.'
              : language === 'ru'
              ? 'Мы используем файлы cookie для обеспечения основных функций веб-сайта и улучшения вашего онлайн-опыта.'
              : 'We use cookies to ensure the basic functionalities of the website and to enhance your online experience.',
          }
        ];

        config.categories.forEach((category: { key: string; is_enabled_by_default: boolean; is_required: boolean; cookies: Array<{ name: string; is_regex: boolean; domain: string; description: string; expiration: string }>; title: string; description: string }) => {
          categories[category.key] = {
            enabled: category.is_enabled_by_default,
            readOnly: category.is_required,
          };

          // Add autoClear for non-necessary cookies
          if (!category.is_required && category.cookies && category.cookies.length > 0) {
            categories[category.key].autoClear = {
              cookies: category.cookies
                .filter(cookie => cookie.is_regex)
                .map(cookie => ({
                  name: new RegExp(cookie.name.replace(/^\/|\/$/g, ''))
                }))
                .concat(
                  category.cookies
                    .filter(cookie => !cookie.is_regex)
                    .map(cookie => ({
                      name: cookie.name
                    }))
                )
            };
          }

          // Build cookie table for modal
          const cookieTable = category.cookies.length > 0 ? {
            headers: {
              name: language === 'de' ? 'Cookie' : language === 'ru' ? 'Cookie' : 'Cookie',
              domain: language === 'de' ? 'Anbieter' : language === 'ru' ? 'Провайдер' : 'Provider',
              desc: language === 'de' ? 'Beschreibung' : language === 'ru' ? 'Описание' : 'Description',
              exp: language === 'de' ? 'Ablauf' : language === 'ru' ? 'Срок действия' : 'Expiration',
            },
            body: category.cookies.map(cookie => ({
              name: cookie.name,
              domain: cookie.domain || window.location.hostname,
              desc: cookie.description,
              exp: cookie.expiration || 'Session',
            }))
          } : undefined;

          // Add section for preferences modal
          sections.push({
            title: category.is_required
              ? `${category.title} <span class="pm__badge">${language === 'de' ? 'Immer aktiviert' : language === 'ru' ? 'Всегда включено' : 'Always Enabled'}</span>`
              : category.title,
            description: category.description,
            linkedCategory: category.key,
            cookieTable
          });
        });

        // Add "More information" section
        sections.push({
          title: language === 'de'
            ? 'Weitere Informationen'
            : language === 'ru'
            ? 'Дополнительная информация'
            : 'More information',
          description: language === 'de'
            ? 'Für Anfragen zu unserer Cookie-Richtlinie und Ihren Optionen, kontaktieren Sie uns bitte.'
            : language === 'ru'
            ? 'По вопросам, связанным с нашей политикой в отношении файлов cookie и вашими вариантами, свяжитесь с нами.'
            : 'For any queries in relation to our policy on cookies and your choices, please contact us.',
        });

        // Initialize vanilla-cookieconsent
        CookieConsent.run({
          categories,

          language: {
            default: language,
            autoDetect: 'browser',
            translations: {
              [language]: {
                consentModal: {
                  title: language === 'de'
                    ? 'Wir verwenden Cookies'
                    : language === 'ru'
                    ? 'Мы используем файлы cookie'
                    : 'We use cookies',
                  description: language === 'de'
                    ? 'Wir verwenden Cookies, um Ihr Browsing-Erlebnis zu verbessern, sichere Authentifizierung bereitzustellen und unseren Traffic zu analysieren. Sie können wählen, welche Cookie-Kategorien Sie zulassen möchten.'
                    : language === 'ru'
                    ? 'Мы используем файлы cookie для улучшения вашего опыта, обеспечения безопасной аутентификации и анализа нашего трафика. Вы можете выбрать, какие категории файлов cookie разрешить.'
                    : 'We use cookies to enhance your browsing experience, provide secure authentication, and analyze our traffic. You can choose which categories of cookies to allow.',
                  acceptAllBtn: language === 'de' ? 'Alle akzeptieren' : language === 'ru' ? 'Принять все' : 'Accept all',
                  acceptNecessaryBtn: language === 'de' ? 'Alle ablehnen' : language === 'ru' ? 'Отклонить все' : 'Reject all',
                  showPreferencesBtn: language === 'de' ? 'Einstellungen verwalten' : language === 'ru' ? 'Управление настройками' : 'Manage preferences',
                  footer: `
                    <a href="/cookie-policy">${language === 'de' ? 'Cookie-Richtlinie' : language === 'ru' ? 'Политика cookie' : 'Cookie Policy'}</a>
                    <a href="/privacy-policy">${language === 'de' ? 'Datenschutzrichtlinie' : language === 'ru' ? 'Политика конфиденциальности' : 'Privacy Policy'}</a>
                  `,
                },
                preferencesModal: {
                  title: language === 'de' ? 'Cookie-Einstellungen' : language === 'ru' ? 'Настройки cookie' : 'Cookie Preferences',
                  acceptAllBtn: language === 'de' ? 'Alle akzeptieren' : language === 'ru' ? 'Принять все' : 'Accept all',
                  acceptNecessaryBtn: language === 'de' ? 'Alle ablehnen' : language === 'ru' ? 'Отклонить все' : 'Reject all',
                  savePreferencesBtn: language === 'de' ? 'Einstellungen speichern' : language === 'ru' ? 'Сохранить настройки' : 'Save preferences',
                  closeIconLabel: language === 'de' ? 'Schließen' : language === 'ru' ? 'Закрыть' : 'Close',
                  sections
                }
              }
            }
          },

          guiOptions: {
            consentModal: {
              layout: 'box inline',
              position: config.ui_settings?.modal_position || 'bottom right',
            },
            preferencesModal: {
              layout: 'box',
              position: 'right',
            }
          },

          revision: config.ui_settings?.revision || 1,
        });

        setIsLoaded(true);
      } catch (error) {
        console.error('Error initializing cookie consent:', error);
      }
    };

    if (!isLoaded) {
      initializeCookieConsent();
    }
  }, [language, isLoaded]);

  return null; // This component doesn't render anything, just initializes the consent banner
}
