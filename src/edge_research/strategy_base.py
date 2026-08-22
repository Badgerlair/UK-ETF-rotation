class StrategyModule:
    name = "base"
    timeframe = ""
    required_columns = []

    def prepare_indicators(self, data, config):
        return data

    def generate_candidates(self, data, config):
        raise NotImplementedError

    def rank_candidates(self, candidates, config):
        return candidates

    def build_orders(self, candidates, portfolio_state, config):
        raise NotImplementedError

