from typing import List, Tuple


def nearest_value_index(values: list[float], target: float) -> int:
    """
    Gibt den Index des numerisch nächsten Wertes aus einer Liste zurück.
    
    Args:
        values: Liste von numerischen Werten
        target: Zielwert, zu dem der nächste Wert gesucht wird
    
    Returns:
        Index des nächsten Wertes in der Liste
    
    Beispiel:
        >>> nearest_value_index([1.0, 2.0, 3.0], 1.9)
        1  # 2.0 ist näher an 1.9 als 1.0
    """
    return min(range(len(values)), key=lambda i: abs(values[i] - target))


def clamp(value: int, min_value: int, max_value: int) -> int:
    """
    Begrenzt einen Wert auf einen Bereich zwischen min_value und max_value.
    
    Stellt sicher, dass Werte innerhalb erlaubter Grenzen liegen.
    
    Args:
        value: Der zu begrenzende Wert
        min_value: Minimale Grenze (inklusive)
        max_value: Maximale Grenze (inklusive)
    
    Returns:
        Der begrenzte Wert innerhalb [min_value, max_value]
    
    Beispiel:
        >>> clamp(5, 0, 10)
        5
        >>> clamp(15, 0, 10)
        10
        >>> clamp(-5, 0, 10)
        0
    """
    return max(min_value, min(value, max_value))


def ev_to_tv_steps(ev: float, third_ev_per_step: float = 1/3) -> int:
    """
    Wandelt Exposure Value (EV) in Belichtungsschritte um.
    
    Konvertiert EV-Werte (z.B. für HDR) in diskrete Belichtungsschritte
    der Kamera (1/3 EV Schritte pro Standard-Stufe).
    
    Args:
        ev: Exposure Value Differenz (z.B. 1.0 für 1 EV)
        third_ev_per_step: EV-Wert pro Schritt (Standard: 1/3 für 1/3 EV Schritte)
    
    Returns:
        Anzahl der Belichtungsschritte (mindestens 1)
    
    Beispiel:
        >>> ev_to_tv_steps(1.0)  # 1 EV mit 1/3 Schritten
        3  # 3 Schritte = 1.0 EV
    """
    return max(1, int(round(ev / third_ev_per_step)))


def round_to_name_index(value: float, names: List[float]) -> int:
    """
    Rundet einen Wert auf den nächsten vorhandenen Namen und gibt dessen Index zurück.

    Args:
        value: Eingabewert
        names: Liste verfügbarer Namenwerte

    Returns:
        Index des nächstgelegenen Wertes in der Liste
    """
    return nearest_value_index(names, value)


def round_to_raw_value(value: float, names: List[float], raw_values: List[int]) -> int:
    """
    Rundet einen Wert auf den nächsten Namen und gibt den zugehörigen Rohwert zurück.

    Args:
        value: Eingabewert
        names: Liste verfügbarer Namenwerte
        raw_values: Liste der zugehörigen Rohwerte

    Returns:
        Rohwert (SDK-Wert) des nächstgelegenen Namens
    """
    idx = round_to_name_index(value, names)
    return raw_values[idx]


def round_to_name_and_raw(
    value: float,
    names: List[float],
    raw_values: List[int],
) -> Tuple[float, int]:
    """
    Rundet einen Wert auf den nächsten Namen und gibt Namen und Rohwert zurück.

    Args:
        value: Eingabewert
        names: Liste verfügbarer Namenwerte
        raw_values: Liste der zugehörigen Rohwerte

    Returns:
        Tupel aus (Name, Rohwert)
    """
    idx = round_to_name_index(value, names)
    return names[idx], raw_values[idx]

def round_base_tv_to_name(base_tv: float, tv_names: list[float]) -> Tuple[int, float]:
    """
    Rundet einen Basis-TV-Wert auf den nächsten vorhandenen Namenwert.

    Args:
        base_tv: Basis-TV-Wert
        tv_names: Liste verfügbarer TV-Werte

    Returns:
        Tupel aus (Index, TV-Wert)
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
    """
    Generiert die Indizes der TV-Werte für eine HDR-Aufnahmeserie.

    Berechnet basierend auf Basisbelichtung, Anzahl der Bilder und EV-Abstand
    die passenden TV-Indizes aus der gegebenen Liste.

    Args:
        base_tv: Basis-TV-Wert (Belichtungszeit)
        hdr_shots: Anzahl der HDR-Aufnahmen
        hdr_ev: EV-Abstand zwischen den Aufnahmen
        tv_names: Liste verfügbarer TV-Werte
        third_ev_per_step: EV pro Schritt (Standard: 1/3)

    Returns:
        Liste von Indizes der TV-Werte für jede Aufnahme
    """
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
    Generiert die TV-Namen für eine HDR-Aufnahmeserie.

    Nutzt die berechneten Indizes, um die entsprechenden TV-Werte
    aus der Namensliste zu extrahieren.

    Args:
        base_tv: Basis-TV-Wert
        hdr_shots: Anzahl der HDR-Aufnahmen
        hdr_ev: EV-Abstand zwischen den Aufnahmen
        tv_names: Liste verfügbarer TV-Werte
        third_ev_per_step: EV pro Schritt (Standard: 1/3)

    Returns:
        Liste der TV-Werte (Namen) für jede Aufnahme
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
    Generiert die SDK-TV-Werte für eine HDR-Aufnahmeserie.

    Wandelt die berechneten TV-Indizes in die zugehörigen
    Rohwerte (SDK-Werte) um.

    Args:
        base_tv: Basis-TV-Wert
        hdr_shots: Anzahl der HDR-Aufnahmen
        hdr_ev: EV-Abstand zwischen den Aufnahmen
        tv_names: Liste verfügbarer TV-Werte
        tv_values: Liste der zugehörigen SDK-Werte
        third_ev_per_step: EV pro Schritt (Standard: 1/3)

    Returns:
        Liste der SDK-TV-Werte für jede Aufnahme
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
    """
    Wandelt eine Liste von Indizes in die zugehörigen Rohwerte um.

    Args:
        indices: Liste von Indizes
        raw_values: Liste der Rohwerte

    Returns:
        Liste der Rohwerte entsprechend der Indizes
    """
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