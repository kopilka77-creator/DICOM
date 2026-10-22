# -*- coding: utf-8 -*-
import math


class _Measure:
    __slots__ = ("p1", "p2", "known_mm", "is_calibration",
                 "label_dx", "label_dy")

    def __init__(self, p1, p2, known_mm=None, is_calibration=False):
        self.p1 = [float(p1[0]), float(p1[1])]
        self.p2 = [float(p2[0]), float(p2[1])]
        self.known_mm = known_mm
        self.is_calibration = is_calibration
        self.label_dx = 0.0
        self.label_dy = 0.0

    @property
    def dist_px(self):
        dx = self.p2[0] - self.p1[0]
        dy = self.p2[1] - self.p1[1]
        return math.sqrt(dx * dx + dy * dy)

    def mid(self):
        return ((self.p1[0] + self.p2[0]) / 2.0 + self.label_dx,
                (self.p1[1] + self.p2[1]) / 2.0 + self.label_dy)