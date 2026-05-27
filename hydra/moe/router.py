"""PyTorch MLP router for HYDRA-MoE soft regime routing."""

import numpy as np
import torch
import torch.nn as nn


class HydraRouter(nn.Module):
    """Soft regime router mapping regime features to expert routing weights via 2-layer MLP."""

    def __init__(
        self,
        input_dim: int,
        n_experts: int = 4,
        hidden_dims: list[int] = None,
        dropout: float = 0.2,
        temperature: float = 1.0,
    ):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [128, 64]

        self.n_experts = n_experts
        self.temperature = temperature

        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            prev_dim = h_dim
        layers.append(nn.Linear(prev_dim, n_experts))

        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning softmax routing weights.

        Args:
            x: (batch, input_dim) router features.

        Returns:
            weights: (batch, n_experts) softmax routing weights summing to 1.
        """
        logits = self.net(x)
        return torch.softmax(logits / self.temperature, dim=-1)

    def get_hard_assignments(self, x: torch.Tensor) -> torch.Tensor:
        """Return argmax expert assignment per sample."""
        with torch.no_grad():
            weights = self.forward(x)
            return weights.argmax(dim=-1)

    def entropy_loss(self, weights: torch.Tensor) -> torch.Tensor:
        """Entropy regularization — penalizes routing all weight to one expert.

        Returns negative entropy (to be minimized), encouraging specialization
        while preventing collapse.
        """
        return -torch.mean(torch.sum(weights * torch.log(weights + 1e-8), dim=1))


class RouterTrainer:
    """Manages router optimization with gradient updates."""

    def __init__(
        self,
        router: HydraRouter,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        lambda_entropy: float = 0.01,
        device: str = "cpu",
    ):
        self.router = router
        self.lambda_entropy = lambda_entropy
        self.device = device
        self.optimizer = torch.optim.Adam(
            router.parameters(), lr=lr, weight_decay=weight_decay
        )
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=500, eta_min=lr * 0.1
        )

    def step(
        self,
        x_router: torch.Tensor,
        expert_probas: np.ndarray,
        y_true: torch.Tensor,
    ) -> dict:
        """One gradient step on router given fixed expert predictions.

        Args:
            x_router: (batch, n_router_features) tensor on device.
            expert_probas: (batch, n_experts) numpy — expert P(long) predictions.
            y_true: (batch,) tensor — true binary labels.

        Returns:
            Dict with bce_loss, entropy_loss, total_loss values.
        """
        self.router.train()
        self.optimizer.zero_grad()

        weights = self.router(x_router)  # (batch, K)

        expert_probas_t = torch.tensor(expert_probas, dtype=torch.float32, device=self.device)
        moe_proba = (weights * expert_probas_t).sum(dim=1)  # (batch,)
        moe_proba = torch.clamp(moe_proba, 1e-7, 1 - 1e-7)

        bce = nn.functional.binary_cross_entropy(moe_proba, y_true.float())
        ent = self.router.entropy_loss(weights)
        total = bce + self.lambda_entropy * ent

        total.backward()
        torch.nn.utils.clip_grad_norm_(self.router.parameters(), max_norm=1.0)
        self.optimizer.step()

        return {
            "bce_loss": bce.item(),
            "entropy_loss": ent.item(),
            "total_loss": total.item(),
        }

    def step_scheduler(self):
        """Step learning rate scheduler."""
        self.scheduler.step()
