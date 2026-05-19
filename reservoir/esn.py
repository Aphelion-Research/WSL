"""Echo State Network implementation."""
import numpy as np
from scipy import sparse
from scipy.sparse import linalg as sp_linalg
from typing import Tuple

from reservoir.config import (
    RESERVOIR_SIZE,
    SPECTRAL_RADII,
    LEAK_RATES,
    SPARSITY,
    INPUT_SCALING,
    WASHOUT_STEPS
)


class EchoStateNetwork:
    """Echo State Network with leaky integrator neurons."""

    def __init__(
        self,
        n_inputs: int,
        reservoir_size: int = RESERVOIR_SIZE,
        spectral_radius: float = 0.95,
        leak_rate: float = 0.3,
        sparsity: float = SPARSITY,
        input_scaling: float = INPUT_SCALING,
        random_state: int = 42
    ):
        """Initialize ESN.

        Args:
            n_inputs: Number of input features
            reservoir_size: Number of reservoir nodes
            spectral_radius: Max eigenvalue of reservoir weight matrix
            leak_rate: Leak rate for leaky integrator
            sparsity: Sparsity of reservoir connections
            input_scaling: Scale of input weights
            random_state: Random seed
        """
        self.n_inputs = n_inputs
        self.reservoir_size = reservoir_size
        self.spectral_radius = spectral_radius
        self.leak_rate = leak_rate
        self.input_scaling = input_scaling
        self.random_state = random_state

        np.random.seed(random_state)

        # Input weights: uniform random [-input_scaling, input_scaling]
        self.W_in = np.random.uniform(
            -input_scaling, input_scaling,
            size=(reservoir_size, n_inputs)
        )

        # Reservoir weights: sparse random, scaled to spectral_radius
        self.W = self._generate_reservoir_weights(reservoir_size, sparsity, spectral_radius)

        # Bias
        self.W_bias = np.random.uniform(-0.1, 0.1, size=reservoir_size)

        # Internal state
        self.state = np.zeros(reservoir_size)

    def _generate_reservoir_weights(
        self,
        size: int,
        sparsity: float,
        spectral_radius: float
    ) -> sparse.csr_matrix:
        """Generate sparse reservoir weight matrix with desired spectral radius."""
        # Generate sparse random matrix
        W = sparse.rand(size, size, density=sparsity, format='csr')
        W.data = np.random.randn(len(W.data))

        # Scale to desired spectral radius
        eigenvalues = sp_linalg.eigs(W, k=1, which='LM', return_eigenvectors=False)
        max_eigenvalue = np.abs(eigenvalues[0])

        if max_eigenvalue > 0:
            W = W * (spectral_radius / max_eigenvalue)

        return W

    def reset(self):
        """Reset internal state."""
        self.state = np.zeros(self.reservoir_size)

    def step(self, u: np.ndarray) -> np.ndarray:
        """Single forward step.

        Args:
            u: Input vector (n_inputs,)

        Returns:
            New state (reservoir_size,)
        """
        # Compute pre-activation
        pre_activation = (
            self.W_in @ u +
            self.W @ self.state +
            self.W_bias
        )

        # Update state with leaky integrator
        new_state = (1 - self.leak_rate) * self.state + self.leak_rate * np.tanh(pre_activation)

        self.state = new_state

        return self.state

    def run(self, inputs: np.ndarray, washout: int = WASHOUT_STEPS) -> np.ndarray:
        """Run ESN on sequence of inputs.

        Args:
            inputs: Input sequence (n_steps, n_inputs)
            washout: Number of initial steps to discard

        Returns:
            State trajectory (n_steps - washout, reservoir_size)
        """
        self.reset()

        states = []

        for t in range(len(inputs)):
            state = self.step(inputs[t])

            if t >= washout:
                states.append(state)

        return np.array(states)


class MultiScaleESN:
    """3-reservoir ESN stack for multi-timescale dynamics."""

    def __init__(self, n_inputs: int, random_state: int = 42):
        """Initialize 3-scale ESN.

        Args:
            n_inputs: Number of input features
            random_state: Random seed
        """
        # Reduced reservoir sizes for memory efficiency
        self.fast = EchoStateNetwork(
            n_inputs,
            reservoir_size=1000,  # Reduced from 5000
            spectral_radius=SPECTRAL_RADII["fast"],
            leak_rate=LEAK_RATES["fast"],
            random_state=random_state
        )

        self.medium = EchoStateNetwork(
            n_inputs,
            reservoir_size=1000,
            spectral_radius=SPECTRAL_RADII["medium"],
            leak_rate=LEAK_RATES["medium"],
            random_state=random_state + 1
        )

        self.slow = EchoStateNetwork(
            n_inputs,
            reservoir_size=1000,
            spectral_radius=SPECTRAL_RADII["slow"],
            leak_rate=LEAK_RATES["slow"],
            random_state=random_state + 2
        )

    def reset(self):
        """Reset all reservoirs."""
        self.fast.reset()
        self.medium.reset()
        self.slow.reset()

    def run(self, inputs: np.ndarray, washout: int = WASHOUT_STEPS) -> np.ndarray:
        """Run all reservoirs and concatenate states.

        Args:
            inputs: Input sequence (n_steps, n_inputs)
            washout: Washout steps

        Returns:
            Concatenated states (n_steps - washout, 3000)
        """
        fast_states = self.fast.run(inputs, washout)
        medium_states = self.medium.run(inputs, washout)
        slow_states = self.slow.run(inputs, washout)

        # Concatenate
        combined = np.hstack([fast_states, medium_states, slow_states])

        return combined
