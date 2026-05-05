"""평가 등급 헬퍼 (◎/○/△)."""


def grade_value(score: float) -> str:
    """A 가치주 점수(낮을수록 좋음)."""
    if score < 0.15:
        return "◎ 매우 저평가"
    if score < 0.30:
        return "○ 저평가"
    return "△ 양호"


def grade_div(div: float) -> str:
    if div >= 8:
        return f"◎ 초고배당({div:.1f}%)"
    if div >= 5:
        return f"○ 고배당({div:.1f}%)"
    return f"△ 일반({div:.1f}%)"


def grade_bluechip(rank: int) -> str:
    if rank <= 3:
        return f"◎ 대장주(#{rank})"
    if rank <= 7:
        return f"○ 우량주(#{rank})"
    return f"△ 중대형(#{rank})"


def grade_momentum(vol_ratio: float) -> str:
    if vol_ratio >= 3:
        return f"◎ 강한신호(거래량 {vol_ratio:.1f}배)"
    if vol_ratio >= 2:
        return f"○ 양호(거래량 {vol_ratio:.1f}배)"
    return f"△ 보통(거래량 {vol_ratio:.1f}배)"


def grade_oversold(rsi: float) -> str:
    if rsi < 20:
        return f"◎ 극과매도(RSI {rsi:.0f})"
    if rsi < 25:
        return f"○ 과매도(RSI {rsi:.0f})"
    return f"△ 약과매도(RSI {rsi:.0f})"


def grade_short_term(score: float) -> str:
    if score >= 12:
        return "◎ 강세"
    if score >= 8:
        return "○ 양호"
    return "△ 보통"
