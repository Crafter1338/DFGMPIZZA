from typing import List, Tuple

def nearest_value_index(values: list[float], target: float) -> int:
    """
    Gibt den Index des numerisch nächsten Wertes zurück.
    Rückgabe: Index
    """
    return min(range(len(values)), key=lambda i: abs(values[i] - target))


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


def ev_to_tv_steps(ev: float, third_ev_per_step: float = 1/3) -> int:
    """
    Wandelt EV in Schritte innerhalb der tv_names Liste um.
    """
    return max(1, int(round(ev / third_ev_per_step)))


def round_to_name_index(value: float, names: List[float]) -> int:
    """
    Rundet einen Input auf den nächsten vorhandenen Namen
    und gibt dessen Index zurück.
    Rückgabe: Index
    """
    return nearest_value_index(names, value)


def round_to_raw_value(value: float, names: List[float], raw_values: List[int]) -> int:
    """
    Rundet einen Input auf den nächsten Namen und gibt
    den zugehörigen SDK Wert zurück.
    Rückgabe: SDK Wert
    """
    idx = round_to_name_index(value, names)
    return raw_values[idx]


def round_to_name_and_raw(
    value: float,
    names: List[float],
    raw_values: List[int],
) -> Tuple[float, int]:
    """
    Rundet einen Input auf den nächsten Namen und gibt sowohl den Namen
    als auch den SDK Wert zurück.
    Rückgabe: (Name, SDK Wert)
    """
    idx = round_to_name_index(value, names)
    return names[idx], raw_values[idx]


def round_base_tv_to_name(base_tv: float, tv_names: list[float]) -> Tuple[int, float]:
    """
    Rundet base_tv auf den nächsten vorhandenen Namenwert.
    Rückgabe: (Index, Name)
    """
    idx = nearest_value_index(tv_names, base_tv)
    return idx, tv_names[idx]


def generate_hdr_tv_name_indices(
    base_tv: float,
    hdr_shots: int,
    hdr_ev: float,
    tv_names: list[float],
    third_ev_per_step: float = 1/3,
) -> List[int]:

    if hdr_shots <= 0:
        return []

    base_idx, _ = round_base_tv_to_name(base_tv, tv_names)
    step_count = ev_to_tv_steps(hdr_ev, third_ev_per_step)

    center = (hdr_shots - 1) / 2

    result = []
    for shot_idx in range(hdr_shots):

        relative_ev_steps = round((shot_idx - center) * step_count)

        tv_idx = clamp(
            base_idx + relative_ev_steps,
            0,
            len(tv_names) - 1
        )

        result.append(tv_idx)

    return result


def generate_hdr_tv_names(
    base_tv: float,
    hdr_shots: int,
    hdr_ev: float,
    tv_names: list[float],
    third_ev_per_step: float = 1/3,
) -> List[float]:
    """
    Generiert die SDK TV Namen. (Wird aktuell nicht gebraucht)
    """

    indices = generate_hdr_tv_name_indices(
        base_tv=base_tv,
        hdr_shots=hdr_shots,
        hdr_ev=hdr_ev,
        tv_names=tv_names,
        third_ev_per_step=third_ev_per_step,
    )

    return [tv_names[i] for i in indices]


def generate_hdr_tv_values(
    base_tv: float,
    hdr_shots: int,
    hdr_ev: float,
    tv_names: list[float],
    tv_values: list[int],
    third_ev_per_step: float = 1/3,
) -> List[int]:
    """
    Generiert die SDK TV Werte.
    """

    indices = generate_hdr_tv_name_indices(
        base_tv,
        hdr_shots,
        hdr_ev,
        tv_names,
        third_ev_per_step
    )

    return [tv_values[i] for i in indices]


def index_to_raw(indices: List[int], raw_values: List[int]) -> List[int]:
    return [raw_values[i] for i in indices]


"""
Verwendungsbeispiel (Notiz an mich selbst):

iso_raw = round_to_raw_value(
    iso_input,
    self.iso_names,
    self.iso_values
)

tv_raw_values = generate_hdr_tv_values(
    base_tv=settings.camera.base_tv,
    hdr_shots=settings.camera.hdr_shot_count,
    hdr_ev=settings.camera.hdr_ev,
    tv_names=self.tv_names,
    tv_values=self.tv_values
)
"""