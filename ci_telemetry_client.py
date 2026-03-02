import os
import sys
import time
import json
import subprocess
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class TestResult:
    test_name: str
    status: str  # PASS/FAIL/SKIP
    duration_ms: int
    error_message: Optional[str] = None

@dataclass
class BuildEvent:
    agent_id: str
    build_id: str
    status: str
    duration_ms: int
    metadata: Optional[Dict] = None

class TelemetryClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
    
    def send_event(self, event: BuildEvent) -> bool:
        """Send build event to telemetry dashboard"""
        try:
            response = requests.post(
                self.endpoint,
                json=asdict(event),
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send telemetry: {e}", file=sys.stderr)
            return False

class TestRunner:
    def __init__(self, telemetry_client: TelemetryClient):
        self.client = telemetry_client
        self.agent_id = os.getenv("CI_AGENT_ID", "local-agent")
        self.build_id = os.getenv("CI_BUILD_ID", f"local-{int(time.time())}")
    
    def run_test_suite(self, test_command: str, test_name: str) -> TestResult:
        """Run a test suite and capture results"""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if result.returncode == 0:
                status = "PASS"
                error_message = None
            else:
                status = "FAIL"
                error_message = result.stderr[:500]  # Truncate error
            
            return TestResult(
                test_name=test_name,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return TestResult(
                test_name=test_name,
                status="FAIL",
                duration_ms=duration_ms,
                error_message="Test timeout after 5 minutes"
            )
    
    def run_with_retry(self, test_command: str, test_name: str, max_retries: int = 3) -> List[TestResult]:
        """Run test multiple times to detect flakiness"""
        results = []
        
        for attempt in range(max_retries):
            print(f"Running {test_name} (attempt {attempt + 1}/{max_retries})...")
            result = self.run_test_suite(test_command, test_name)
            results.append(result)
            
            # Send individual result
            event = BuildEvent(
                agent_id=self.agent_id,
                build_id=f"{self.build_id}-{test_name}-attempt{attempt+1}",
                status=result.status,
                duration_ms=result.duration_ms,
                metadata={
                    "test_name": test_name,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": result.error_message
                }
            )
            self.client.send_event(event)
            
            # If test passes, no need to retry
            if result.status == "PASS" and attempt == 0:
                break
        
        return results
    
    def analyze_flakiness(self, results: List[TestResult]) -> Dict:
        """Analyze test results for flakiness"""
        statuses = [r.status for r in results]
        unique_statuses = set(statuses)
        
        is_flaky = len(unique_statuses) > 1
        pass_count = statuses.count("PASS")
        fail_count = statuses.count("FAIL")
        
        return {
            "is_flaky": is_flaky,
            "total_runs": len(results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "success_rate": pass_count / len(results) if results else 0,
            "avg_duration_ms": sum(r.duration_ms for r in results) / len(results) if results else 0
        }

# Example usage
if __name__ == "__main__":
    # Initialize telemetry client
    endpoint = os.getenv("TELEMETRY_ENDPOINT", "http://localhost:8888/metrics")
    client = TelemetryClient(endpoint)
    runner = TestRunner(client)
    
    # Define test suites
    test_suites = [
        ("pytest tests/test_api.py -v", "test_api"),
        ("pytest tests/test_database.py -v", "test_database"),
        ("pytest tests/test_integration.py -v", "test_integration"),
    ]
    
    all_results = {}
    
    for test_command, test_name in test_suites:
        # Run with retry to detect flakiness
        results = runner.run_with_retry(test_command, test_name, max_retries=3)
        analysis = runner.analyze_flakiness(results)
        all_results[test_name] = analysis
        
        # Print analysis
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print(f"Flaky: {analysis['is_flaky']}")
        print(f"Success Rate: {analysis['success_rate']:.1%}")
        print(f"Average Duration: {analysis['avg_duration_ms']:.0f}ms")
        print(f"{'='*60}\n")
    
    # Print summary
    print("\n" + "="*60)
    print("FLAKY TEST SUMMARY")
    print("="*60)
    flaky_tests = [name for name, analysis in all_results.items() if analysis['is_flaky']]
    
    if flaky_tests:
        print(f"⚠️  {len(flaky_tests)} flaky test(s) detected:")
        for test_name in flaky_tests:
            analysis = all_results[test_name]
            print(f"  - {test_name}: {analysis['success_rate']:.1%} success rate")
    else:
        print("✅ No flaky tests detected!")
    
    # Exit with failure if any flaky tests found
    sys.exit(1 if flaky_tests else 0)