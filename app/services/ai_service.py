def analyze_phishing_messages(messages: list[str]) -> dict:
    full_text = " ".join(messages)

    rules = [
        {
            "keywords": ["검찰", "경찰", "금융감독원"],
            "reason": "기관 사칭 표현 감지",
            "score": 30,
        },
        {
            "keywords": ["현금", "인출", "출금"],
            "reason": "현금 인출 요구 감지",
            "score": 30,
        },
        {
            "keywords": ["가족에게", "알리지", "비밀"],
            "reason": "비밀 유지 요구 감지",
            "score": 25,
        },
        {
            "keywords": ["지정 장소", "가져오세요", "전달"],
            "reason": "현금 전달 요구 감지",
            "score": 20,
        },
        {
            "keywords": ["계좌", "범죄", "연루"],
            "reason": "계좌 범죄 연루 위협 표현 감지",
            "score": 20,
        },
    ]

    score = 0
    reasons = []

    for rule in rules:
        if any(keyword in full_text for keyword in rule["keywords"]):
            score += rule["score"]
            reasons.append(rule["reason"])

    score = min(score, 100)

    if score >= 70:
        risk_level = "DANGER"
        summary = "보이스피싱 가능성이 매우 높은 대화입니다."

    elif score >= 30:
        risk_level = "CAUTION"
        summary = "보이스피싱 의심 요소가 포함된 대화입니다."

    else:
        risk_level = "SAFE"
        summary = "현재 대화에서 뚜렷한 보이스피싱 위험 요소가 발견되지 않았습니다."

    return {
        "risk_level": risk_level,
        "risk_score": score,
        "reasons": reasons,
        "summary": summary,
    }
