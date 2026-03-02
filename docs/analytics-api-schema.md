# Analytics API Schema

This document describes the separation of analytics endpoints and their use cases.

## Endpoint Overview

| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `GET /api/emails/analytics` | Email-specific dashboard: sent, delivered, opened, clicked, replied, bounced; by-template breakdown; timeline | EmailAnalyticsSection (E-Mail page) |
| `GET /api/emails/analytics/overview` | Flat overview: total_sent, open_rate, click_rate, response_rate, bounce_rate | Legacy / alternative views |
| `GET /api/analytics/conversion-health` | Business conversion metrics: delivery rate, open rate (simulated), reply rate, conversion rate; uses StatusHistory for real conversions | Dashboard, Analytics page |

## Schema Details

### GET /api/emails/analytics (EmailAnalyticsDashboard)

- **overview**: total_sent, delivered, opened, clicked, replied, bounced
- **rates**: open_rate, click_rate, reply_rate, bounce_rate
- **by_template**: per-template sent/opened/rate
- **timeline**: daily sent/opened

### GET /api/analytics/conversion-health

- **period_days**: int
- **metrics**: total_sent, total_failed, delivery_rate, opens, open_rate, replies, reply_rate, conversions, conversion_rate

Conversion and reply rates are derived from `StatusHistory` (PENDING, GEWONNEN transitions), not from email tracking pixels.
