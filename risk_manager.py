# ==========================================
# FILE: risk_manager.py
# ==========================================
class RiskManager:
    """Evaluates market setups and account criteria to prevent catastrophic downsides."""
    
    def __init__(self, max_position_size_pct: float = 0.10, max_open_positions: int = 5):
        self.max_position_size_pct = max_position_size_pct
        self.max_open_positions = max_open_positions

    def evaluate_order_safety(self, current_balance: float, asset_price: float, quantity: int, current_position_count: int) -> dict:
        order_value = asset_price * quantity
        allocation_pct = order_value / (current_balance + 1e-10)
        
        if current_position_count >= self.max_open_positions:
            return {
                "approved": False, 
                "reason": f"Risk Threshold Met: Maximum open positions ({self.max_open_positions}) reached."
            }
            
        if allocation_pct > self.max_position_size_pct:
            max_allowed_qty = int((current_balance * self.max_position_size_pct) // asset_price)
            return {
                "approved": False, 
                "reason": f"Risk Threshold Met: Order allocation ({allocation_pct:.1%}) exceeds maximum limit ({self.max_position_size_pct:.1%}). Max allowed quantity: {max_allowed_qty}"
            }
            
        if quantity <= 0 or asset_price <= 0:
            return {"approved": False, "reason": "Invalid transaction inputs: price and quantity must be positive numbers."}

        return {"approved": True, "reason": "Order approved by risk parameters."}