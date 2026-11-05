from server import config, policy

config.MOCK_LLM = True


def test_offline_compile_keeps_domains_intact():
    rules, err = policy.compile_policy("Never send email outside acme.example. Ask me before any payment over $50.")
    assert err is None and len(rules) == 2 and rules[0]["text"] == "Never send email outside acme.example"
    assert rules[0]["condition"]["not_domain"] == "acme.example" and rules[0]["verdict"] == "deny"
    assert rules[1]["tool"] == "transfer_money" and rules[1]["condition"]["max_amount"] == 50.0 and rules[1]["verdict"] == "ask"


def test_clean_drops_invalid_rules():
    out = policy.clean([{"tool": "nope", "verdict": "deny"}, {"tool": "run_shell", "verdict": "deny", "condition": {"regex": "(", "arg": "cmd"}},
                        {"tool": "run_shell", "verdict": "ask", "condition": {"arg": "cmd", "regex": "curl", "bogus": 1}}])
    assert len(out) == 1 and "bogus" not in out[0]["condition"]


def test_empty_policy_errors():
    rules, err = policy.compile_policy("   ")
    assert rules == [] and err
