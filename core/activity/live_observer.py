"""Conservative visible movement summaries, independent of procedure steps."""
import math


class LiveObserver:
    def __init__(self):
        self.previous = {}

    def describe(self, state):
        parts = []
        current = {}
        scale = max(state.frame_width, state.frame_height, 1)
        for hand in state.hands:
            if hand.confidence < 0.6:
                continue
            name = hand.hand_type.value.lower()
            x, y = hand.wrist
            old = self.previous.get(name)
            moving = False
            if old and 0 < state.timestamp - old[0] < 0.8:
                moving = math.hypot(x-old[1], y-old[2]) / scale / (state.timestamp-old[0]) > 0.06
            current[name] = (state.timestamp, x, y)
            nearby = []
            points = [(x, y)] + [(p.x, p.y) for p in hand.keypoints if p.confidence >= 0.6]
            for obj in state.objects:
                if obj.class_name.lower() in {"person", "astronaut"} or obj.confidence < 0.45:
                    continue
                b = obj.bbox
                distance = min(math.hypot(max(b.x1-px, 0, px-b.x2), max(b.y1-py, 0, py-b.y2)) for px, py in points)
                if distance <= 0.035 * scale:
                    nearby.append(obj.class_name)
            item = f"{name} hand {'moving' if moving else 'visible / steady'}"
            item += f" near {', '.join(sorted(set(nearby)))} (grip unverified)" if nearby else "; no recognized object near hand"
            parts.append(item)
        self.previous = current
        if not parts:
            return "Person visible; hands not visible" if state.poses else "No person or hands detected"
        return " | ".join(parts)
