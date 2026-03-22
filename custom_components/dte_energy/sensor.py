from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, CURRENCY_DOLLAR
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DTEDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DTEDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DTEAmountDueSensor(coordinator),
        DTEElectricChargeSensor(coordinator),
        DTEAverageDailyCostSensor(coordinator),
        DTELastPaymentSensor(coordinator),
        DTEDueDateSensor(coordinator),
        DTEBillingPeriodSensor(coordinator),
        DTEPeakUsageSensor(coordinator),
        DTEOffpeakUsageSensor(coordinator),
        DTETotalUsageSensor(coordinator),
        DTERateCategorySensor(coordinator),
        DTELastReadingDateSensor(coordinator),
    ])


# ------------------------------------------------------------------
# Base class
# ------------------------------------------------------------------

class DTEBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: DTEDataCoordinator, key: str, name: str):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"DTE {name}"
        self._attr_unique_id = f"dte_energy_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key) if self.coordinator.data else None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.account_number)},
            "name": "DTE Energy",
            "manufacturer": "DTE Energy",
            "model": "Residential Account",
        }


# ------------------------------------------------------------------
# Bill sensors
# ------------------------------------------------------------------

class DTEAmountDueSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "amount_due", "Amount Due")
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = CURRENCY_DOLLAR


class DTEElectricChargeSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "electric_charge", "Electric Charge")
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = CURRENCY_DOLLAR


class DTEAverageDailyCostSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "average_daily_cost", "Average Daily Cost")
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = CURRENCY_DOLLAR


class DTELastPaymentSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "last_payment_amount", "Last Payment Amount")
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = CURRENCY_DOLLAR


class DTEDueDateSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "due_date", "Due Date")
        self._attr_icon = "mdi:calendar-clock"


class DTEBillingPeriodSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "billing_period", "Billing Period")
        self._attr_icon = "mdi:calendar-range"


# ------------------------------------------------------------------
# Usage sensors
# ------------------------------------------------------------------

class DTEPeakUsageSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "today_peak_kwh", "Peak Usage")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {"last_reading_date": self.coordinator.data.get("last_reading_date")}


class DTEOffpeakUsageSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "today_offpeak_kwh", "Off-Peak Usage")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:lightning-bolt-outline"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {"last_reading_date": self.coordinator.data.get("last_reading_date")}


class DTETotalUsageSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "today_total_kwh", "Total Usage")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:meter-electric"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {"last_reading_date": self.coordinator.data.get("last_reading_date")}


class DTERateCategorySensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "rate_category", "Rate Category")
        self._attr_icon = "mdi:tag"


class DTELastReadingDateSensor(DTEBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "last_reading_date", "Last Reading Date")
        self._attr_icon = "mdi:calendar-check"