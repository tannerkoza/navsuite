import navtools.conversions as ntc


def test_ecef_conversions():
    assert ntc.ecef2lla(1.0, 1.0, 1.0) == True


if __name__ == "__main__":
    test_ecef_conversions()
