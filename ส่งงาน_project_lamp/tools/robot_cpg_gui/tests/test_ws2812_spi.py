"""SPI NeoPixel tests use fake hardware; they do NOT access GPIO."""
from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.robot_cpg_gui.led_gpio import (
    LedGpioConfig, LedGpioDriver, parse_led_config, save_led_config, load_led_config,
)


class FakeSpi:
    def __init__(self):
        self.closed = False

    def deinit(self):
        self.closed = True


class FakePixels:
    instances = []

    def __init__(self, bus, count, **kwargs):
        self.bus = bus
        self.count = count
        self.kwargs = kwargs
        self.values = [(0, 0, 0)] * count
        self.shows = 0
        self.__class__.instances.append(self)

    def __setitem__(self, i, value):
        self.values[i] = tuple(value)

    def fill(self, value):
        self.values = [tuple(value)] * self.count

    def show(self):
        self.shows += 1


class Ws2812SpiTests(unittest.TestCase):
    def setUp(self):
        FakePixels.instances.clear()
        self.spi = FakeSpi()
        self.patcher = patch.dict(sys.modules, {
            'board': types.SimpleNamespace(SPI=lambda: self.spi),
            'neopixel_spi': types.SimpleNamespace(NeoPixel_SPI=FakePixels),
        })
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_default_config_keeps_outputs_off(self):
        cfg = load_led_config(Path(__file__).parents[1] / 'led_gpio.json')
        self.assertEqual(cfg.mode, 'ws2812_pio')
        self.assertEqual(cfg.data_bcm, 12)
        self.assertFalse(cfg.enabled)
        driver = LedGpioDriver(cfg)
        self.assertFalse(driver.outputs)
        self.assertIsNone(driver._pixel)
        self.assertEqual(FakePixels.instances, [])

    def test_validates_pixel_count_brightness_and_fixed_spi_data_pin(self):
        with self.assertRaises(ValueError):
            parse_led_config({'schema_version': 1, 'enabled': True, 'mode': 'ws2812_spi', 'data_bcm': 18})
        with self.assertRaises(ValueError):
            parse_led_config({'schema_version': 1, 'enabled': True, 'mode': 'ws2812_spi', 'pixel_count': 0})
        with self.assertRaises(ValueError):
            parse_led_config({'schema_version': 1, 'enabled': True, 'mode': 'ws2812_spi', 'max_brightness': 1.0})
        with self.assertRaises(ValueError):
            parse_led_config({'schema_version': 1, 'enabled': True, 'mode': 'ws2812_spi', 'pixel_order': 'RGBW'})
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'led_gpio.json'
            cfg = LedGpioConfig(enabled=True, mode='ws2812_spi', data_bcm=10, pixel_count=12, max_brightness=0.2)
            save_led_config(p, cfg)
            self.assertEqual(load_led_config(p), cfg)

    def test_single_pixel_color_brightness_off_and_close(self):
        driver = LedGpioDriver(LedGpioConfig(enabled=True, mode='ws2812_spi', data_bcm=10, max_brightness=0.2))
        pixels = FakePixels.instances[-1]
        self.assertEqual(pixels.count, 1)
        self.assertEqual(pixels.kwargs['pixel_order'], 'GRB')
        driver.update({'color': '#ff0000', 'brightness': 1.0})
        self.assertEqual(pixels.values, [(51, 0, 0)])
        last_shows = pixels.shows
        driver.update({'color': '#ff0000', 'brightness': 1.0})
        self.assertEqual(pixels.shows, last_shows)
        driver.update({'color': '#ff0000', 'brightness': 1.0}, enabled=False)
        self.assertEqual(pixels.values, [(0, 0, 0)])
        driver.close()
        self.assertTrue(self.spi.closed)
        self.assertEqual(pixels.values, [(0, 0, 0)])

    def test_rainbow_spatial_and_empty_on_error(self):
        driver = LedGpioDriver(LedGpioConfig(enabled=True, mode='ws2812_spi', data_bcm=10, pixel_count=8))
        pixels = FakePixels.instances[-1]
        driver.update({'color': '#ff0000', 'brightness': 1.0, 'pattern': 'rainbow'})
        self.assertGreater(len(set(pixels.values)), 4)
        self.assertTrue(all(max(px) <= 64 for px in pixels.values))
        driver.update({'color': 'not-a-color', 'brightness': 1.0})
        self.assertEqual(pixels.values, [(0, 0, 0)] * 8)
        driver.off()
        self.assertEqual(pixels.values, [(0, 0, 0)] * 8)
        driver.close()


if __name__ == '__main__':
    unittest.main()
