#! /usr/bin/python

import logging
import unittest
from unittest import TestCase

import config_pb2

import beevacay
from beevacay import (Brick, VacationSegment, ONE_DAY)

logging.basicConfig(level=logging.DEBUG)

def apply_vacation_segment(road, vacay, runits='d'):
  """Convenience function to allow human-readable tests."""
  road = [b._replace(date=None if b.date is None else b.date * ONE_DAY)
      for b in road]
  vacay = vacay._replace(start=vacay.start * ONE_DAY, end=vacay.end * ONE_DAY)
  result = beevacay.apply_vacation_segment(road, runits, vacay)
  return [b._replace(date=None if b.date is None else int(b.date / ONE_DAY))
      for b in result]

class ApplyVacationSegmentTestsRates(TestCase):
    def test_minimalist_road(self):
        road = [
          Brick(0, 0, None),
          Brick(20, None, 1),
        ]
        vacay = VacationSegment(5, 10, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 1),
          Brick(10, None, 0),
          Brick(20, None, 1),
        ])

    def test_basics(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, None, 1),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(5, 10, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(10, None, 0),
          Brick(20, None, 1),
          Brick(31, None, 5),
        ])

    def test_more_basics(self):
        road = [
          Brick(100, 55, None),
          Brick(107, None, 3),
          Brick(120, None, 1),
          Brick(130, None, 5),
          Brick(131, None, 5),
        ]
        vacay = VacationSegment(105, 110, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(105, None, 3),
          Brick(110, None, 0),
          Brick(120, None, 1),
          Brick(131, None, 5),
        ])

    def test_non_zero_rate(self):
        road = [
          Brick(100, 55, None),
          Brick(107, None, 3),
          Brick(120, None, 1),
          Brick(130, None, 5),
          Brick(131, None, 5),
        ]
        vacay = VacationSegment(105, 110, 999, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(105, None, 3),
          Brick(110, None, 999),
          Brick(120, None, 1),
          Brick(131, None, 5),
        ])

    def test_interior_rates(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(8, None, 500),
          Brick(9, None, -999),
          Brick(10, None, 500),
          Brick(20, None, 1),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(5, 10, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(10, None, 0),
          Brick(20, None, 1),
          Brick(31, None, 5),
        ])

    def test_vacation_into_the_future(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, None, 1),
        ]
        vacay = VacationSegment(5, 25, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(20, None, 0),
        ])

    def test_past_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
        ]
        vacay = VacationSegment(-10, -5, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, None, 3),
        ])

    def test_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
        ]
        vacay = VacationSegment(50, 100, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, None, 3),
        ])

    def test_past_and_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, None, 1),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(-50, 100, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(31, None, 0),
        ])

    def test_idempotency(self):
        road = [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(10, None, 0),
          Brick(20, None, 1),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(5, 10, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay), road)

    def test_widen(self):
        road = [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(10, None, 0),
          Brick(20, None, 1),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(5, 11, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(11, None, 0),
          Brick(20, None, 1),
          Brick(31, None, 5),
        ])

    def test_shrink(self):
        road = [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(10, None, 0),
          Brick(20, None, 1),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(5, 9, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(10, None, 0),
          Brick(20, None, 1),
          Brick(31, None, 5),
        ])

    def test_runits(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, None, 1),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(5, 10, 0, None)
        self.assertEquals(apply_vacation_segment(road,vacay, 'w'),
          [
          Brick(0, 0, None),
          Brick(5, None, 3),
          Brick(10, None, 0),
          Brick(20, None, 1),
          Brick(31, None, 5),
        ])

class ApplyVacationSegmentTestsTotalsDiscardTotals(TestCase):
    def test_minimalist_road(self):
        road = [
          Brick(0, 0, None),
          Brick(20, 20, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 1),
          Brick(10, None, 0),
          Brick(20, None, 1),
        ])

    def test_basics(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, None, 1.0),
          Brick(10, None, 0),
          Brick(20, None, 1.0),
          Brick(30, 40, None),
        ])

    def test_more_basics(self):
        self.maxDiff = 100000
        road = [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ]
        vacay = VacationSegment(105, 110, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(105, None, 2.0),
          Brick(110, None, 0),
          Brick(120, None, 2.0),
          Brick(130, 115, None),
        ])

    def test_non_zero_rate(self):
        road = [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ]
        vacay = VacationSegment(105, 110, 999, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(105, None, 2.0),
          Brick(110, None, 999),
          Brick(120, None, 2.0),
          Brick(130, 115, None),
        ])

    def test_interior_rates(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(8, None, 500),
          Brick(9, None, -999),
          Brick(10, None, 800),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, None, 1.0),
          Brick(10, None, 0),
          Brick(20, None, 1.0),
          Brick(30, 40, None),
        ])

    def test_vacation_into_the_future(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, 20, None),
        ]
        vacay = VacationSegment(5, 25, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, None, 1.0),
          Brick(20, None, 0),
        ])

    def test_past_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ]
        vacay = VacationSegment(-10, -5, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ])

    def test_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ]
        vacay = VacationSegment(50, 100, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ])

    def test_past_and_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, 20, None),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(-50, 100, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(31, None, 0),
        ])

    def test_idempotency(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, None, 1.0),
          Brick(10, None, 0),
          Brick(20, None, 1.0),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.DISCARD_TOTALS)
        self.assertEquals(apply_vacation_segment(road,vacay), road)

class ApplyVacationSegmentTestsTotalsReachBeforeVacation(TestCase):
    def test_minimalist_road(self):
        road = [
          Brick(0, 0, None),
          Brick(20, 20, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, 10, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
        ])

    def test_basics(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])

    def test_more_basics(self):
        self.maxDiff = 100000
        road = [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ]
        vacay = VacationSegment(105, 110, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(105, 75.0, None),
          Brick(110, None, 0),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ])

    def test_non_zero_rate(self):
        road = [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ]
        vacay = VacationSegment(105, 110, 999, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(105, 75.0, None),
          Brick(110, None, 999),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ])


    def test_interior_rates(self):
        self.maxDiff = 100000
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(8, None, 500),
          Brick(9, None, -999),
          Brick(10, None, 800),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])

    def test_vacation_into_the_future(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, 20, None),
        ]
        vacay = VacationSegment(5, 25, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, 20.0, None),
          Brick(20, None, 0),
        ])

    def test_past_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ]
        vacay = VacationSegment(-10, -5, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ])

    def test_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ]
        vacay = VacationSegment(50, 100, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ])

    def test_past_and_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, 20, None),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(-50, 100, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(0, 31, None),
          Brick(31, None, 0),
        ])

    def test_idempotency(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay), road)

    def test_widen(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 11, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay), [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(11, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])

    def test_shrink(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 9, 0, config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay), [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(9, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])

class ApplyVacationSegmentTestsTotalsReachAfterVacation(TestCase):
    def test_minimalist_road(self):
        road = [
          Brick(0, 0, None),
          Brick(20, 20, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, 5.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
        ])

    def test_basics(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 5.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])

    def test_more_basics(self):
        self.maxDiff = 100000
        road = [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ]
        vacay = VacationSegment(105, 110, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(105, 65.0, None),
          Brick(110, None, 0),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ])

    def test_non_zero_rate(self):
        road = [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ]
        vacay = VacationSegment(105, 110, 999, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(100, 55, None),
          Brick(103, 61, None),
          Brick(105, 65.0, None),
          Brick(110, None, 999),
          Brick(120, 95, None),
          Brick(130, 115, None),
        ])

    def test_interior_rates(self):
        self.maxDiff = 100000
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(8, None, 500),
          Brick(9, None, -999),
          Brick(10, None, 800),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 5.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])

    def test_vacation_into_the_future(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, 20, None),
        ]
        vacay = VacationSegment(5, 25, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(5, 5.0, None),
          Brick(20, None, 0),
          Brick(21, 20, None),
        ])

    def test_past_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ]
        vacay = VacationSegment(-10, -5, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ])

    def test_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ]
        vacay = VacationSegment(50, 100, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(7, 7, None),
        ])

    def test_past_and_future_vacation(self):
        road = [
          Brick(0, 0, None),
          Brick(7, None, 3),
          Brick(20, 20, None),
          Brick(30, None, 5),
          Brick(31, None, 5),
        ]
        vacay = VacationSegment(-50, 100, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay),
          [
          Brick(0, 0, None),
          Brick(31, None, 0),
          Brick(32, 20, None),
        ])

    def test_idempotency(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 5.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 10, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay), road)

    def test_widen(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 11, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay), [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(11, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])

    def test_shrink(self):
        road = [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(10, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ]
        vacay = VacationSegment(5, 9, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION)
        self.assertEquals(apply_vacation_segment(road,vacay), [
          Brick(0, 0, None),
          Brick(3, 3, None),
          Brick(5, 10.0, None),
          Brick(9, None, 0),
          Brick(20, 20, None),
          Brick(30, 40, None),
        ])


if __name__ == '__main__':
    unittest.main()