# 태양 황경으로 현재 24절기를 계산합니다(Meeus 저정밀식, 오차 수 분 이내).
from datetime import datetime, timezone
from math import floor, radians, sin

# 황경 0°(춘분)부터 15°마다 하나씩
TERMS = ('춘분', '청명', '곡우', '입하', '소만', '망종', '하지', '소서', '대서', '입추', '처서', '백로',
         '추분', '한로', '상강', '입동', '소설', '대설', '동지', '소한', '대한', '입춘', '우수', '경칩')


def solar_longitude(moment):
    days = (moment - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400
    t = days / 36525
    mean = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    anomaly = radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    center = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * sin(anomaly)
              + (0.019993 - 0.000101 * t) * sin(2 * anomaly) + 0.000289 * sin(3 * anomaly))
    apparent = mean + center - 0.00569 - 0.00478 * sin(radians(125.04 - 1934.136 * t))
    return apparent % 360


def solar_term(moment=None):
    moment = moment or datetime.now(timezone.utc)
    return TERMS[floor(solar_longitude(moment) / 15) % 24]
