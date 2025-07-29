__all__ = []

import warnings

import aspn23_lcm
import lcm

ASPN_MODULES = {"aspn23": aspn23_lcm}


class AspnDecoderLcm:
    def __init__(self, standard: str | list[str] = list(ASPN_MODULES.keys())):
        standard = [standard] if isinstance(standard, str) else standard

        self._classes = []

        for s in standard:
            module = ASPN_MODULES[s.casefold()]
            standard_classes = [
                (s, cls) for cls in module.__dict__.values() if isinstance(cls, type)
            ]

            self._classes.extend(standard_classes)

    def decode(self, msg: lcm.Event) -> tuple[str, object]:
        msg_fp = msg.data[:8]

        for standard, cls in self._classes:
            if msg_fp == cls._get_packed_fingerprint():
                decoded_data = cls.decode(msg.data)

                return standard, decoded_data

        err_msg = f"unable to decode message on channel: {msg.channel}."
        warnings.warn(
            message=err_msg,
            category=RuntimeWarning,
            stacklevel=2,
        )
