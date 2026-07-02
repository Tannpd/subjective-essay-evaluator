import pytest
import json

def test_initial_state(direct_deploy):
    # Deploy the contract specifying the v0.2.16 SDK version
    contract = direct_deploy("contracts/subjective_essay_evaluator.py", sdk_version="v0.2.16")
    
    # Check that next_id is initially 0
    assert contract.get_total_evaluations() == 0

def test_input_validation(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/subjective_essay_evaluator.py", sdk_version="v0.2.16")
    
    # Test empty submission_text
    with pytest.raises(Exception) as excinfo:
        contract.evaluate_submission("", "Some rubric")
    assert "submission_text must not be empty" in str(excinfo.value)
    
    # Test empty rubric
    with pytest.raises(Exception) as excinfo:
        contract.evaluate_submission("Some essay", "")
    assert "rubric must not be empty" in str(excinfo.value)

def test_evaluate_submission_happy_path(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/subjective_essay_evaluator.py", sdk_version="v0.2.16")
    
    # Mock LLM response
    # The contract uses gl.nondet.exec_prompt
    direct_vm.mock_llm(
        r".*",
        '{"verdict": "EXCELLENT", "score": 92, "feedback": "Amazing essay!"}'
    )
    
    # Run evaluation
    contract.evaluate_submission("A great essay on gravity", "Assess grammar and flow")
    
    # Check state was updated
    assert contract.get_total_evaluations() == 1
    
    # Get evaluation results
    eval_json = contract.get_evaluation("0")
    result = json.loads(eval_json)
    
    assert result["id"] == "0"
    assert result["submission_text"] == "A great essay on gravity"
    assert result["rubric"] == "Assess grammar and flow"
    assert result["verdict"] == "EXCELLENT"
    assert result["score"] == 92
    assert result["feedback"] == "Amazing essay!"
