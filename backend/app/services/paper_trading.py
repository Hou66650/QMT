from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.schemas import PaperAccount, PaperOrder, PaperPosition, Quote


class PaperTradingService:
    """Manual paper-trading ledger. It never connects to an order execution API."""

    def __init__(self, path: Path, initial_cash: float = 1_000_000):
        if initial_cash <= 0:
            raise ValueError("模拟账户初始资金必须大于 0")
        self.path = path
        self.initial_cash = round(float(initial_cash), 2)
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(self._empty_state())

    def _empty_state(self) -> dict:
        return {"initial_cash": self.initial_cash, "cash": self.initial_cash, "positions": {}, "orders": []}

    def _read(self) -> dict:
        with self._lock:
            try:
                state = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return self._empty_state()
            state.setdefault("initial_cash", self.initial_cash)
            state.setdefault("cash", state["initial_cash"])
            state.setdefault("positions", {})
            state.setdefault("orders", [])
            return state

    def _write(self, state: dict) -> None:
        with self._lock:
            self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def position_codes(self) -> list[str]:
        return list(self._read()["positions"])

    def list_orders(self, limit: int = 50) -> list[PaperOrder]:
        orders = self._read()["orders"][-limit:]
        return [PaperOrder.model_validate(item) for item in reversed(orders)]

    def execute(self, code: str, side: str, quantity: int, quote: Quote) -> PaperOrder:
        if quantity <= 0:
            raise ValueError("委托数量必须大于 0")
        if quote.price <= 0:
            raise ValueError("当前行情价格不可用")

        with self._lock:
            state = self._read()
            positions = state["positions"]
            position = positions.get(code)
            price = round(float(quote.price), 4)
            amount = round(price * quantity, 2)
            realized_pnl = 0.0

            if side == "buy":
                if amount > float(state["cash"]) + 1e-9:
                    raise ValueError("模拟账户可用资金不足")
                previous_quantity = int(position["quantity"]) if position else 0
                previous_cost = float(position["average_cost"]) if position else 0.0
                next_quantity = previous_quantity + quantity
                average_cost = ((previous_cost * previous_quantity) + amount) / next_quantity
                positions[code] = {
                    "code": code,
                    "name": quote.name,
                    "quantity": next_quantity,
                    "average_cost": round(average_cost, 4),
                }
                state["cash"] = round(float(state["cash"]) - amount, 2)
            elif side == "sell":
                if not position or int(position["quantity"]) < quantity:
                    raise ValueError("模拟持仓数量不足")
                average_cost = float(position["average_cost"])
                realized_pnl = round((price - average_cost) * quantity, 2)
                remaining = int(position["quantity"]) - quantity
                if remaining:
                    position["quantity"] = remaining
                else:
                    positions.pop(code)
                state["cash"] = round(float(state["cash"]) + amount, 2)
            else:
                raise ValueError("仅支持 buy 或 sell")

            order = PaperOrder(
                id=uuid4().hex[:12], code=code, name=quote.name, side=side,
                quantity=quantity, price=price, amount=amount, realized_pnl=realized_pnl,
                executed_at=datetime.now(timezone.utc), provider=quote.provider, is_mock=quote.is_mock,
            )
            state["orders"].append(order.model_dump(mode="json"))
            self._write(state)
            return order

    def account(self, quotes: dict[str, Quote] | None = None) -> PaperAccount:
        state = self._read()
        quotes = quotes or {}
        positions: list[PaperPosition] = []
        market_value = 0.0

        for code, item in state["positions"].items():
            quantity = int(item["quantity"])
            average_cost = float(item["average_cost"])
            quote = quotes.get(code)
            market_price = float(quote.price) if quote else average_cost
            position_value = market_price * quantity
            unrealized_pnl = (market_price - average_cost) * quantity
            positions.append(PaperPosition(
                code=code, name=str(item.get("name") or code), quantity=quantity,
                average_cost=round(average_cost, 4), market_price=round(market_price, 4),
                market_value=round(position_value, 2), unrealized_pnl=round(unrealized_pnl, 2),
                unrealized_pnl_percent=round(((market_price / average_cost) - 1) * 100, 2) if average_cost else 0,
            ))
            market_value += position_value

        cash = round(float(state["cash"]), 2)
        initial_cash = round(float(state["initial_cash"]), 2)
        total_assets = round(cash + market_value, 2)
        return PaperAccount(
            initial_cash=initial_cash, cash=cash, market_value=round(market_value, 2),
            total_assets=total_assets, total_pnl=round(total_assets - initial_cash, 2),
            positions=positions, orders_count=len(state["orders"]), real_trading_enabled=False,
        )
