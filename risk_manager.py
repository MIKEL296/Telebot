import pandas as pd

class RiskManager:
    """Evaluates market setups and account criteria to prevent catastrophic downsides."""
    
    def __init__(self, max_position_size_pct: float = 0.10, max_open_positions: int = 5):
        self.max_position_size_pct = max_position_size_pct
        self.max_open_positions = max_open_positions

    def evaluate_order_safety(self, current_balance: float, asset_price: float, quantity: int, current_position_count: int) -> dict:
        """
        Validates whether an intended order meets the safety guidelines.
        Returns a dict indicating confirmation or denial reasons.
        """
        order_value = asset_price * quantity
        allocation_pct = order_value / (current_balance + 1e-10)
        
        # 1. Position Limit Check
        if current_position_count >= self.max_open_positions:
            return {
                "approved": False, 
                "reason": f"Risk Threshold Met: Maximum open positions ({self.max_open_positions}) reached."
            }
            
        # 2. Maximum Allocation / Exposure Check
        if allocation_pct > self.max_position_size_pct:
            max_allowed_qty = int((current_balance * self.max_position_size_pct) // asset_price)
            return {
                "approved": False, 
                "reason": f"Risk Threshold Met: Order allocation ({allocation_pct:.1%}) exceeds maximum limit ({self.max_position_size_pct:.1%}). Max allowed quantity: {max_allowed_qty}"
            }
            
        # 3. Basic Check for Invalid Inputs
        if quantity <= 0 or asset_price <= 0:
            return {"approved": False, "reason": "Invalid transaction inputs: price and quantity must be positive numbers."}

        return {"approved": True, "reason": "Order approved by risk parameters."}


if __name__ == "__main__":
    print("Testing Risk Manager module calculations...")
    rm = RiskManager(max_position_size_pct=0.10, max_open_positions=3)
    
    # Context settings for a mock test
    account_cash = 50000.00
    stock_price = 150.00
    
    # Test Scenario 1: A massive order exceeding bounds
    bad_order = rm.evaluate_order_safety(account_cash, stock_price, quantity=100, current_position_count=1)
    print(f"\nScenario A (100 shares): Approved={bad_order['approved']} | Reason: {bad_order['reason']}")
    
    # Test Scenario 2: A safe order inside parameters
    good_order = rm.evaluate_order_safety(account_cash, stock_price, quantity=10, current_position_count=1)
    print(f"Scenario B (10 shares): Approved={good_order['approved']} | Reason: {good_order['reason']}")