# DTE Energy Home Assistant Integration

Custom integration for DTE Energy that provides energy usage and billing sensors.

## Setup

1. Copy `custom_components/dte_energy/` to your HA `config/custom_components/` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration** and search for **DTE Energy**
4. Get your `webSecurityToken`:
   - Log into [newlook.dteenergy.com](https://newlook.dteenergy.com)
   - Open DevTools (F12) → Application → Cookies → `newlook.dteenergy.com`
   - Copy the `webSecurityToken` value
5. Paste it into the setup form along with your account number

## Re-authentication

If HA shows a re-authentication notification it means the token chain was broken
(usually because HA was down for more than 40 minutes). Just log into the DTE 
site again, grab a fresh token and paste it in.

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.dte_amount_due` | Current amount due |
| `sensor.dte_electric_charge` | Electric charge for billing period |
| `sensor.dte_average_daily_cost` | Average daily cost |
| `sensor.dte_last_payment_amount` | Most recent payment |
| `sensor.dte_due_date` | Payment due date |
| `sensor.dte_billing_period` | Current billing period dates |
| `sensor.dte_peak_usage` | Most recent day peak kWh |
| `sensor.dte_off_peak_usage` | Most recent day off-peak kWh |
| `sensor.dte_total_usage` | Most recent day total kWh |
| `sensor.dte_rate_category` | Current rate plan code |
| `sensor.dte_last_reading_date` | Date of most recent usage reading |

## Notes

- Usage data is typically delayed by 1-2 days from DTE
- Tokens refresh automatically every 30 minutes
- Integration will notify you if re-authentication is needed