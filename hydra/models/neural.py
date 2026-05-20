"""Neural models: MLP (sklearn), LSTM, TCN (PyTorch)."""
from __future__ import annotations

from typing import Optional

import numpy as np

from hydra.models.base import ModelWrapper

MLP_PARAMS = dict(
    hidden_layer_sizes=(256, 128, 64, 32), activation="relu",
    solver="adam", alpha=1e-4, batch_size=256, learning_rate_init=1e-3,
    max_iter=300, early_stopping=True, validation_fraction=0.15,
    n_iter_no_change=20, random_state=42,
)

LSTM_PARAMS = dict(
    seq_len=60, hidden=128, layers=2, dropout=0.2,
    bidirectional=False, lr=1e-3, batch=256, epochs=50,
    patience=8, weight_decay=1e-4,
)

TCN_PARAMS = dict(
    seq_len=60, channels=[64, 64, 64, 64], kernel=3,
    dropout=0.2, lr=1e-3, batch=256, epochs=50, patience=8,
)


class MLPModel(ModelWrapper):
    name = "mlp"

    def __init__(self, **kwargs):
        self.params = {**MLP_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.neural_network import MLPClassifier
        self.model = MLPClassifier(**self.params)
        self.model.fit(X, y)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        self.model.warm_start = True
        self.model.max_iter += 10
        self.model.fit(X, y)
        return self


class LSTMModel(ModelWrapper):
    name = "lstm"

    def __init__(self, **kwargs):
        self.params = {**LSTM_PARAMS, **kwargs}
        self.model = None
        self._torch_available = None

    def _check_torch(self):
        if self._torch_available is None:
            try:
                import torch
                self._torch_available = True
            except ImportError:
                self._torch_available = False
        return self._torch_available

    def _make_sequences(self, X, y=None):
        seq_len = self.params["seq_len"]
        n = len(X)
        if n <= seq_len:
            return X[np.newaxis, :, :], y[:1] if y is not None else None
        seqs = []
        labels = []
        for i in range(seq_len, n):
            seqs.append(X[i - seq_len:i])
            if y is not None:
                labels.append(y[i])
        return np.array(seqs), np.array(labels) if y is not None else None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if not self._check_torch():
            from sklearn.neural_network import MLPClassifier
            self.model = MLPClassifier(
                hidden_layer_sizes=(128, 64), max_iter=100, random_state=42)
            self.model.fit(X, y)
            return self

        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        X_seq, y_seq = self._make_sequences(X, y)
        n_feat = X.shape[1]
        p = self.params

        class LSTMNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.lstm = nn.LSTM(n_feat, p["hidden"], p["layers"],
                                    dropout=p["dropout"], batch_first=True)
                self.fc = nn.Linear(p["hidden"], 1)

            def forward(self, x):
                out, _ = self.lstm(x)
                return torch.sigmoid(self.fc(out[:, -1, :]))

        device = "cuda" if torch.cuda.is_available() else "cpu"
        net = LSTMNet().to(device)
        opt = torch.optim.AdamW(net.parameters(), lr=p["lr"],
                                weight_decay=p["weight_decay"])
        criterion = nn.BCELoss()

        ds = TensorDataset(
            torch.FloatTensor(X_seq).to(device),
            torch.FloatTensor(y_seq).to(device),
        )
        dl = DataLoader(ds, batch_size=p["batch"], shuffle=True)

        best_loss = float("inf")
        patience_counter = 0
        for epoch in range(p["epochs"]):
            net.train()
            epoch_loss = 0.0
            for xb, yb in dl:
                pred = net(xb).squeeze()
                loss = criterion(pred, yb)
                opt.zero_grad()
                loss.backward()
                opt.step()
                epoch_loss += loss.item()
            if epoch_loss < best_loss:
                best_loss = epoch_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= p["patience"]:
                    break

        self.model = net
        self._device = device
        self._n_feat = n_feat
        return self

    def predict_proba(self, X):
        if not self._check_torch() or not hasattr(self, "_device"):
            return self.model.predict_proba(X)[:, 1]

        import torch
        X_seq, _ = self._make_sequences(X)
        self.model.eval()
        with torch.no_grad():
            t = torch.FloatTensor(X_seq).to(self._device)
            proba = self.model(t).cpu().numpy().flatten()
        pad = np.full(len(X) - len(proba), 0.5)
        return np.concatenate([pad, proba])

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        if not self._check_torch():
            return self.fit(X, y, sample_weight, X_val, y_val)

        import torch
        from torch.utils.data import DataLoader, TensorDataset

        X_seq, y_seq = self._make_sequences(X, y)
        for pg in self.model.parameters():
            pg.requires_grad_(True)

        opt = torch.optim.AdamW(self.model.parameters(),
                                lr=self.params["lr"] / 10)
        criterion = torch.nn.BCELoss()
        ds = TensorDataset(
            torch.FloatTensor(X_seq).to(self._device),
            torch.FloatTensor(y_seq).to(self._device),
        )
        dl = DataLoader(ds, batch_size=self.params["batch"], shuffle=True)
        self.model.train()
        for xb, yb in dl:
            pred = self.model(xb).squeeze()
            loss = criterion(pred, yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
        return self


class TCNModel(ModelWrapper):
    name = "tcn"

    def __init__(self, **kwargs):
        self.params = {**TCN_PARAMS, **kwargs}
        self.model = None
        self._torch_available = None

    def _check_torch(self):
        if self._torch_available is None:
            try:
                import torch
                self._torch_available = True
            except ImportError:
                self._torch_available = False
        return self._torch_available

    def _make_sequences(self, X, y=None):
        seq_len = self.params["seq_len"]
        n = len(X)
        if n <= seq_len:
            return X[np.newaxis, :, :].transpose(0, 2, 1), y[:1] if y is not None else None
        seqs = []
        labels = []
        for i in range(seq_len, n):
            seqs.append(X[i - seq_len:i].T)
            if y is not None:
                labels.append(y[i])
        return np.array(seqs), np.array(labels) if y is not None else None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if not self._check_torch():
            from sklearn.neural_network import MLPClassifier
            self.model = MLPClassifier(
                hidden_layer_sizes=(128, 64), max_iter=100, random_state=42)
            self.model.fit(X, y)
            return self

        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        X_seq, y_seq = self._make_sequences(X, y)
        n_feat = X.shape[1]
        p = self.params

        class TCNBlock(nn.Module):
            def __init__(self, in_ch, out_ch, kernel, dilation):
                super().__init__()
                pad = (kernel - 1) * dilation
                self.conv = nn.Conv1d(in_ch, out_ch, kernel,
                                      dilation=dilation, padding=pad)
                self.bn = nn.BatchNorm1d(out_ch)
                self.drop = nn.Dropout(p["dropout"])
                self.residual = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

            def forward(self, x):
                out = self.drop(torch.relu(self.bn(self.conv(x)[:, :, :x.size(2)])))
                return out + self.residual(x)

        class TCNNet(nn.Module):
            def __init__(self):
                super().__init__()
                channels = [n_feat] + p["channels"]
                layers = []
                for i in range(len(channels) - 1):
                    layers.append(TCNBlock(channels[i], channels[i + 1],
                                           p["kernel"], dilation=2**i))
                self.net = nn.Sequential(*layers)
                self.fc = nn.Linear(channels[-1], 1)

            def forward(self, x):
                out = self.net(x)
                return torch.sigmoid(self.fc(out[:, :, -1]))

        device = "cuda" if torch.cuda.is_available() else "cpu"
        net = TCNNet().to(device)
        opt = torch.optim.AdamW(net.parameters(), lr=p["lr"])
        criterion = nn.BCELoss()

        ds = TensorDataset(
            torch.FloatTensor(X_seq).to(device),
            torch.FloatTensor(y_seq).to(device),
        )
        dl = DataLoader(ds, batch_size=p["batch"], shuffle=True)

        best_loss = float("inf")
        patience_counter = 0
        for epoch in range(p["epochs"]):
            net.train()
            epoch_loss = 0.0
            for xb, yb in dl:
                pred = net(xb).squeeze()
                loss = criterion(pred, yb)
                opt.zero_grad()
                loss.backward()
                opt.step()
                epoch_loss += loss.item()
            if epoch_loss < best_loss:
                best_loss = epoch_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= p["patience"]:
                    break

        self.model = net
        self._device = device
        return self

    def predict_proba(self, X):
        if not self._check_torch() or not hasattr(self, "_device"):
            return self.model.predict_proba(X)[:, 1]

        import torch
        X_seq, _ = self._make_sequences(X)
        self.model.eval()
        with torch.no_grad():
            t = torch.FloatTensor(X_seq).to(self._device)
            proba = self.model(t).cpu().numpy().flatten()
        pad = np.full(len(X) - len(proba), 0.5)
        return np.concatenate([pad, proba])

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        if not self._check_torch():
            return self.fit(X, y, sample_weight, X_val, y_val)

        import torch
        from torch.utils.data import DataLoader, TensorDataset

        X_seq, y_seq = self._make_sequences(X, y)
        opt = torch.optim.AdamW(self.model.parameters(),
                                lr=self.params["lr"] / 10)
        criterion = torch.nn.BCELoss()
        ds = TensorDataset(
            torch.FloatTensor(X_seq).to(self._device),
            torch.FloatTensor(y_seq).to(self._device),
        )
        dl = DataLoader(ds, batch_size=self.params["batch"], shuffle=True)
        self.model.train()
        for xb, yb in dl:
            pred = self.model(xb).squeeze()
            loss = criterion(pred, yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
        return self
