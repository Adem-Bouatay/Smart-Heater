import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from "react-native";

export default function App() {
  const [ws, setWs] = useState(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [temp, setTemp] = useState(null);
  const [target, setTarget] = useState("");
  const [heating, setHeating] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("Connecting...");

  useEffect(() => {
    const socket = new WebSocket("ws://YOUR_PUBLIC_IP:8765");

    socket.onopen = () => {
      console.log("Connected to server");
      setConnectionStatus("Connected - Please login");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "auth") {
        setAuthenticated(data.success);
      } else {
        setTemp(data.temperature);
        setHeating(data.heating);
        if (data.target) setTarget(data.target.toString());
      }
    };

    socket.onerror = (e) => {
      console.error("WebSocket error:", e.message);
      setConnectionStatus("Connection failed");
    };

    socket.onclose = () => {
      console.log("Disconnected");
      setConnectionStatus("Disconnected");
    };

    setWs(socket);

    return () => socket.close();
  }, []);

  const handleLogin = (username, password) => {
    if (ws) {
      ws.send(JSON.stringify({ type: "login", username, password }));
    }
  };

  const sendTargetTemp = () => {
    if (ws && authenticated) {
      ws.send(JSON.stringify({ target: parseFloat(target) }));
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      {!authenticated ? (
        <LoginForm onLogin={handleLogin} connectionStatus={connectionStatus} />
      ) : (
        <ThermostatControl
          temp={temp}
          heating={heating}
          target={target}
          setTarget={setTarget}
          sendTargetTemp={sendTargetTemp}
          logout={() => setAuthenticated(false)}
        />
      )}
    </KeyboardAvoidingView>
  );
}

function LoginForm({ onLogin, connectionStatus }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("1234");

  return (
    <View style={styles.authContainer}>
      <Text style={styles.title}>Thermostat Controller</Text>
      <Text style={styles.connectionStatus}>{connectionStatus}</Text>

      <TextInput
        style={styles.input}
        placeholder="Username"
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      <TouchableOpacity
        style={styles.loginButton}
        onPress={() => onLogin(username, password)}
      >
        <Text style={styles.buttonText}>Login</Text>
      </TouchableOpacity>
    </View>
  );
}

function ThermostatControl({
  temp,
  heating,
  target,
  setTarget,
  sendTargetTemp,
  logout,
}) {
  return (
    <View style={styles.controlContainer}>
      <Text style={styles.sectionTitle}>Thermostat Control</Text>

      <View style={styles.statusContainer}>
        <Text style={styles.temperature}>{temp}°C</Text>
        <View
          style={[
            styles.heatingIndicator,
            { backgroundColor: heating ? "#ff4444" : "#44ff44" },
          ]}
        >
          <Text style={styles.heatingText}>{heating ? "HEATING" : "IDLE"}</Text>
        </View>
      </View>

      <Text style={styles.label}>Set Target Temperature:</Text>
      <TextInput
        style={styles.input}
        keyboardType="numeric"
        value={target}
        onChangeText={setTarget}
        placeholder="Enter target temperature"
      />

      <TouchableOpacity style={styles.controlButton} onPress={sendTargetTemp}>
        <Text style={styles.buttonText}>Update Target</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.logoutButton} onPress={logout}>
        <Text style={styles.buttonText}>Logout</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f0f0f0",
  },
  authContainer: {
    flex: 1,
    justifyContent: "center",
    padding: 30,
  },
  controlContainer: {
    flex: 1,
    padding: 30,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#333",
    textAlign: "center",
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: "600",
    color: "#444",
    textAlign: "center",
    marginBottom: 30,
  },
  connectionStatus: {
    textAlign: "center",
    color: "#666",
    marginBottom: 30,
  },
  input: {
    backgroundColor: "white",
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#ddd",
    marginBottom: 15,
    fontSize: 16,
  },
  loginButton: {
    backgroundColor: "#2196F3",
    padding: 15,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  controlButton: {
    backgroundColor: "#4CAF50",
    padding: 15,
    borderRadius: 10,
    alignItems: "center",
    marginVertical: 10,
  },
  logoutButton: {
    backgroundColor: "#f44336",
    padding: 15,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 20,
  },
  buttonText: {
    color: "white",
    fontWeight: "bold",
    fontSize: 16,
  },
  statusContainer: {
    alignItems: "center",
    marginBottom: 30,
  },
  temperature: {
    fontSize: 48,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 20,
  },
  heatingIndicator: {
    paddingVertical: 8,
    paddingHorizontal: 20,
    borderRadius: 15,
    flexDirection: "row",
    alignItems: "center",
  },
  heatingText: {
    color: "white",
    fontWeight: "bold",
    marginLeft: 8,
  },
  label: {
    fontSize: 16,
    color: "#666",
    marginBottom: 10,
  },
});
