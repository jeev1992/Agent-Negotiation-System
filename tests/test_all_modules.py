"""
Test all modules by actually running them.
This is NOT unit tests - this is real integration testing.
"""

import sys
sys.path.insert(0, '.')
import importlib.util


def import_layer(name):
    """Import a numbered layer folder dynamically."""
    spec = importlib.util.spec_from_file_location(name, f'{name}/__init__.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_03_protocol():
    """Test message protocol types."""
    print('Testing 03_protocol...')
    protocol = import_layer('03_protocol')
    
    # Test Offer
    offer = protocol.Offer(price=350.0, message='Test offer')
    print(f'  Created Offer: price={offer.price}, type={offer.type}')
    
    # Test Counter
    counter = protocol.Counter(price=400.0, original_price=350.0, message='Counter')
    print(f'  Created Counter: price={counter.price}')
    
    # Test Accept
    accept = protocol.Accept(price=375.0, message='Deal!')
    print(f'  Created Accept: price={accept.price}')
    
    # Test Reject
    reject = protocol.Reject(reason='Too expensive')
    print(f'  Created Reject: reason={reject.reason}')
    
    print('  ✓ 03_protocol PASSED')


def test_04_fsm():
    """Test finite state machine."""
    print('Testing 04_fsm...')
    fsm_module = import_layer('04_fsm')
    
    # Test lifecycle
    fsm = fsm_module.NegotiationFSM(max_turns=5)
    print(f'  Initial state: {fsm.state}')
    
    fsm.start()
    print(f'  After start: {fsm.state}')
    
    # Accept and check context
    fsm.accept(350.0)
    print(f'  After accept: {fsm.state}, context.agreed_price={fsm.context.agreed_price}')
    
    # Test termination via max turns
    fsm2 = fsm_module.NegotiationFSM(max_turns=3)
    fsm2.start()
    for i in range(5):
        if fsm2.is_active:
            fsm2.process_turn()
    print(f'  After max turns: {fsm2.state}, is_active={fsm2.is_active}')
    
    print('  ✓ 04_fsm PASSED')


def test_05_agents():
    """Test buyer and seller strategies."""
    print('Testing 05_agents...')
    agents = import_layer('05_agents')
    
    # Test buyer strategy
    result = agents.buyer_strategy(
        current_offer=400, 
        max_price=450, 
        turn=1, 
        max_turns=10, 
        previous_offer=None
    )
    print(f'  Buyer strategy: type={result["type"]}, price={result["price"]}')
    
    # Test seller strategy
    result = agents.seller_strategy(
        buyer_offer=350, 
        min_price=300, 
        asking_price=500, 
        turn=1, 
        max_turns=10
    )
    print(f'  Seller strategy: type={result["type"]}, price={result["price"]}')
    
    # Test acceptance
    result = agents.seller_strategy(
        buyer_offer=350, 
        min_price=300, 
        asking_price=500, 
        turn=5, 
        max_turns=10
    )
    print(f'  Seller (turn 5): type={result["type"]}, price={result["price"]}')
    
    print('  ✓ 05_agents PASSED')


def test_07_coordination():
    """Test coordination policy."""
    print('Testing 07_coordination...')
    coord = import_layer('07_coordination')
    
    policy = coord.CoordinationPolicy(buyer_max_price=450, seller_min_price=350)
    print(f'  Policy created: {type(policy).__name__}')
    
    # Test buyer offer validation
    result = policy.validate_buyer_offer(price=400, previous_offer=None)
    print(f'  Buyer offer $400 allowed: {result.allowed}')
    
    # Test seller counter validation
    result = policy.validate_seller_counter(price=380, previous_counter=None)
    print(f'  Seller counter $380 allowed: {result.allowed}')
    
    # Test full action validation
    result = policy.validate_action(
        actor='buyer',
        expected_actor='buyer',
        message_type='offer',
        price=400
    )
    print(f'  Full action validation: {result.allowed}')
    
    print('  ✓ 07_coordination PASSED')


def test_08_transport():
    """Test message transport."""
    print('Testing 08_transport...')
    transport = import_layer('08_transport')
    
    channel = transport.LocalChannel()
    
    # Create a message
    msg = transport.Message(
        sender='buyer',
        recipient='seller',
        payload={'type': 'offer', 'price': 300}
    )
    
    # Track received messages
    received_messages = []
    def on_message(m):
        received_messages.append(m)
    
    # Subscribe and send
    channel.subscribe('seller', on_message)
    channel.send(msg)
    
    print(f'  Sent message ID: {msg.id}')
    print(f'  Messages received by seller: {len(received_messages)}')
    if received_messages:
        print(f'  Payload: {received_messages[0].payload}')
    
    print('  ✓ 08_transport PASSED')


def test_09_context():
    """Test MCP context server."""
    print('Testing 09_context...')
    context = import_layer('09_context')
    
    mcp = context.MCPServer()
    
    # Get pricing rules for enterprise license
    rules = mcp.get_pricing_rules('enterprise-license')
    print(f'  Pricing rules: min={rules["min_price"]}, base={rules["base_price"]}')
    
    # Test with customer segment
    rules = mcp.get_pricing_rules('enterprise-license', customer_segment='enterprise')
    print(f'  Enterprise segment effective min: {rules["effective_min"]}')
    
    print('  ✓ 09_context PASSED')


def test_11_evaluation():
    """Test evaluation judge."""
    print('Testing 11_evaluation...')
    evaluation = import_layer('11_evaluation')
    
    judge = evaluation.NegotiationJudge()
    
    # Test successful negotiation
    judgments = judge.evaluate(
        final_price=400,
        buyer_max=450,
        seller_min=350,
        turns=3,
        success=True,
        messages=[
            {'agent': 'buyer', 'type': 'offer'},
            {'agent': 'seller', 'type': 'counter'},
            {'agent': 'buyer', 'type': 'offer'},
            {'agent': 'seller', 'type': 'accept'}
        ]
    )
    overall = judge.overall_score(judgments)
    print(f'  Successful negotiation score: {overall:.2f}')
    
    # Test failed negotiation
    judgments = judge.evaluate(
        final_price=None,
        buyer_max=200,
        seller_min=300,
        turns=10,
        success=False,
        messages=[]
    )
    overall = judge.overall_score(judgments)
    print(f'  Failed negotiation score: {overall:.2f}')
    
    print('  ✓ 11_evaluation PASSED')


def test_10_runtime():
    """Test runtime (quick demo)."""
    print('Testing 10_runtime...')
    runtime = import_layer('10_runtime')
    
    # Create runtime config
    config = runtime.RuntimeConfig(
        mode='demo',
        verbose=False
    )
    print(f'  Config created: mode={config.mode}')
    
    # Create and initialize runtime
    rt = runtime.NegotiationRuntime(config)
    rt.initialize()
    print('  Runtime initialized')
    
    # Create and run session
    session = rt.create_session(
        buyer_max_price=450,
        seller_min_price=350,
        max_turns=5
    )
    rt.run_session(session)
    print(f'  Session result: agreed={session.agreed}, price={session.final_price}')
    
    rt.shutdown()
    print('  ✓ 10_runtime PASSED')


def main():
    print('=' * 60)
    print('TESTING ALL MODULES')
    print('=' * 60)
    print()
    
    tests = [
        test_03_protocol,
        test_04_fsm,
        test_05_agents,
        test_07_coordination,
        test_08_transport,
        test_09_context,
        test_11_evaluation,
        test_10_runtime,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
            print()
        except Exception as e:
            failed += 1
            print(f'  ✗ FAILED: {e}')
            print()
    
    print('=' * 60)
    print(f'RESULTS: {passed} passed, {failed} failed')
    print('=' * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
