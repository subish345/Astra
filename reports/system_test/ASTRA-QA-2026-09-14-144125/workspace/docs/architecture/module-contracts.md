# ASTRA-EA Module Contracts & Interface Specifications

## 1. Design Philosophy
All modules in ASTRA-EA adhere to the **Single Responsibility Principle** and communicate through strongly typed contracts and abstract interfaces. No module directly accesses internal state or third-party implementations of adjacent modules.

---

## 2. Core Interface Contracts

### 2.1 Camera Ingestion Contract
```python
class CameraSource(ABC):
    @abstractmethod
    def start(self) -> bool: ...
    
    @abstractmethod
    def stop(self) -> None: ...
    
    @abstractmethod
    def read(self) -> Optional[FrameData]: ...
    
    @abstractmethod
    def get_status(self) -> str: ...
    
    @abstractmethod
    def get_fps(self) -> float: ...
    
    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]: ...
```

### 2.2 Perception Contracts
```python
class ObjectDetector(ABC):
    @abstractmethod
    def detect(self, frame: FrameData) -> List[Detection]: ...

class PoseEstimator(ABC):
    @abstractmethod
    def estimate(self, frame: FrameData) -> List[PoseObservation]: ...

class HandDetector(ABC):
    @abstractmethod
    def detect(self, frame: FrameData) -> List[HandObservation]: ...

class Tracker(ABC):
    @abstractmethod
    def update(self, detections: List[Detection], frame_id: int) -> List[Track]: ...
```

### 2.3 Interaction Contract
```python
class InteractionEngine(ABC):
    @abstractmethod
    def process(
        self,
        tracks: List[Track],
        hands: List[HandObservation],
        timestamp: float
    ) -> List[InteractionEvent]: ...
    
    @abstractmethod
    def reset(self) -> None: ...
```

### 2.4 Activity Recognition Contract
```python
class ActivityRecognizer(ABC):
    @abstractmethod
    def update(self, interaction_events: List[InteractionEvent]) -> List[ActivityObservation]: ...
    
    @abstractmethod
    def flush(self) -> List[ActivityObservation]: ...
```

### 2.5 Evidence Aggregation Contract
```python
class EvidenceEngine(ABC):
    @abstractmethod
    def evaluate(
        self,
        activity: ActivityObservation,
        interactions: List[InteractionEvent],
        tracks: List[Track]
    ) -> EvidenceBundle: ...
```

### 2.6 Procedure Engine Contract
```python
class ProcedureEngine(ABC):
    @abstractmethod
    def load_procedure(self, config_path: Path) -> None: ...
    
    @abstractmethod
    def get_current_step(self) -> Optional[ExperimentStep]: ...
    
    @abstractmethod
    def advance_step(self) -> Optional[ExperimentStep]: ...
    
    @abstractmethod
    def reset(self) -> None: ...
```

### 2.7 Assurance Engine Contract
```python
class AssuranceEngine(ABC):
    @abstractmethod
    def evaluate_step(
        self,
        current_step: ExperimentStep,
        activity: ActivityObservation,
        evidence: EvidenceBundle
    ) -> AssuranceDecision: ...
```

### 2.8 Assistance & Guidance Contract
```python
class VoiceManager(ABC):
    @abstractmethod
    def speak(self, text: str, priority: AssistantPriority, cooldown: float = 3.0) -> bool: ...
    
    @abstractmethod
    def stop(self) -> None: ...

class GuidanceEngine(ABC):
    @abstractmethod
    def generate_guidance(self, decision: AssuranceDecision) -> Optional[AssistantMessage]: ...
```

### 2.9 Health Monitoring Contract
```python
class HealthManager(ABC):
    @abstractmethod
    def register_component(self, name: str) -> None: ...
    
    @abstractmethod
    def heartbeat(self, name: str, state: HealthState, metrics: Dict[str, Any]) -> None: ...
    
    @abstractmethod
    def get_overall_health(self) -> HealthState: ...
```
