"""Tests for ESN."""
import pytest
import numpy as np
from scipy.sparse import linalg as sp_linalg

from reservoir.esn import EchoStateNetwork, MultiScaleESN


def test_esn_state_update():
    """Test ESN state updates correctly."""
    np.random.seed(42)

    esn = EchoStateNetwork(n_inputs=3, reservoir_size=100, random_state=42)

    u = np.array([1.0, 0.5, -0.3])

    state1 = esn.step(u)
    state2 = esn.step(u)

    # State should change
    assert not np.allclose(state1, state2)

    # State should be bounded (tanh activation)
    assert np.all(np.abs(state2) <= 1.0)


def test_esn_spectral_radius():
    """Test spectral radius property."""
    np.random.seed(42)

    esn = EchoStateNetwork(n_inputs=3, reservoir_size=100, spectral_radius=0.95, random_state=42)

    # Check spectral radius
    eigenvalues = sp_linalg.eigs(esn.W, k=1, which='LM', return_eigenvectors=False)
    max_eigenvalue = np.abs(eigenvalues[0])

    # Should be close to desired spectral radius
    assert abs(max_eigenvalue - 0.95) < 0.1


def test_esn_washout():
    """Test washout removes transient."""
    np.random.seed(42)

    esn = EchoStateNetwork(n_inputs=3, reservoir_size=100, random_state=42)

    # Generate constant input
    inputs = np.ones((200, 3))

    states = esn.run(inputs, washout=100)

    # Should have 100 states after washout
    assert states.shape[0] == 100


def test_multiscale_esn():
    """Test multi-scale ESN."""
    np.random.seed(42)

    esn = MultiScaleESN(n_inputs=5, random_state=42)

    inputs = np.random.randn(150, 5)

    states = esn.run(inputs, washout=50)

    # Should have 3000 features (3 x 1000)
    assert states.shape == (100, 3000)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
