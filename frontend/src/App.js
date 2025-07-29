import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [status, setStatus] = useState({
    is_running: false,
    current_passphrase: "",
    total_attempts: 0,
    found_keys: 0,
    start_time: null,
    progress: 0
  });
  
  const [results, setResults] = useState([]);
  const [recentAttempts, setRecentAttempts] = useState([]);
  const [testPassphrase, setTestPassphrase] = useState("i love you");
  const [testResult, setTestResult] = useState(null);
  const [stats, setStats] = useState({
    total_attempts: 0,
    total_successful_cracks: 0,
    total_checked_passphrases: 0,
    success_rate_percentage: 0
  });

  // Fetch status every 2 seconds
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${API}/status`);
        setStatus(response.data);
      } catch (error) {
        console.error("Error fetching status:", error);
      }
    };

    const fetchResults = async () => {
      try {
        const response = await axios.get(`${API}/results`);
        setResults(response.data);
      } catch (error) {
        console.error("Error fetching results:", error);
      }
    };

    const fetchRecentAttempts = async () => {
      try {
        const response = await axios.get(`${API}/attempts?limit=10`);
        setRecentAttempts(response.data);
      } catch (error) {
        console.error("Error fetching recent attempts:", error);
      }
    };

    const fetchStats = async () => {
      try {
        const response = await axios.get(`${API}/stats`);
        setStats(response.data);
      } catch (error) {
        console.error("Error fetching stats:", error);
      }
    };

    // Initial fetch
    fetchStatus();
    fetchResults();
    fetchRecentAttempts();
    fetchStats();

    // Set up intervals
    const statusInterval = setInterval(fetchStatus, 2000);
    const resultsInterval = setInterval(fetchResults, 10000);
    const attemptsInterval = setInterval(fetchRecentAttempts, 5000);
    const statsInterval = setInterval(fetchStats, 15000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(resultsInterval);
      clearInterval(attemptsInterval);
      clearInterval(statsInterval);
    };
  }, []);

  const startCracking = async () => {
    try {
      await axios.post(`${API}/start-cracking`);
    } catch (error) {
      console.error("Error starting cracking:", error);
      alert("Error starting cracking: " + error.response?.data?.detail || error.message);
    }
  };

  const stopCracking = async () => {
    try {
      await axios.post(`${API}/stop-cracking`);
    } catch (error) {
      console.error("Error stopping cracking:", error);
    }
  };

  const clearData = async () => {
    if (window.confirm("Are you sure you want to clear all data?")) {
      try {
        await axios.delete(`${API}/clear-data`);
        setResults([]);
        setRecentAttempts([]);
      } catch (error) {
        console.error("Error clearing data:", error);
      }
    }
  };

  const testCrypto = async () => {
    if (!testPassphrase.trim()) return;
    
    try {
      const response = await axios.post(`${API}/test-crypto`, null, {
        params: { passphrase: testPassphrase }
      });
      setTestResult(response.data);
    } catch (error) {
      console.error("Error testing crypto:", error);
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return "N/A";
    return new Date(timestamp).toLocaleString();
  };

  const formatBalance = (balance) => {
    return balance > 0 ? balance.toFixed(8) + " BTC" : "0 BTC";
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-orange-400 mb-2">
            ₿ Bitcoin Passphrase Cracking Bot
          </h1>
          <p className="text-gray-300">
            Searching for simple passphrases used to generate Bitcoin private keys
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Control Panel */}
          <div className="lg:col-span-1">
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-bold mb-4 text-orange-400">Control Panel</h2>
              
              <div className="space-y-4">
                <div className="flex space-x-3">
                  <button
                    onClick={startCracking}
                    disabled={status.is_running}
                    className={`flex-1 px-4 py-2 rounded-md font-medium transition-colors ${
                      status.is_running
                        ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                        : "bg-green-600 hover:bg-green-700 text-white"
                    }`}
                  >
                    {status.is_running ? "Running..." : "Start Cracking"}
                  </button>
                  
                  <button
                    onClick={stopCracking}
                    disabled={!status.is_running}
                    className={`flex-1 px-4 py-2 rounded-md font-medium transition-colors ${
                      !status.is_running
                        ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                        : "bg-red-600 hover:bg-red-700 text-white"
                    }`}
                  >
                    Stop
                  </button>
                </div>
                
                <button
                  onClick={clearData}
                  className="w-full px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md font-medium transition-colors"
                >
                  Clear All Data
                </button>
              </div>
            </div>

            {/* Test Tool */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-bold mb-4 text-orange-400">Test Crypto Functions</h3>
              
              <div className="space-y-3">
                <input
                  type="text"
                  value={testPassphrase}
                  onChange={(e) => setTestPassphrase(e.target.value)}
                  placeholder="Enter test passphrase"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400"
                />
                
                <button
                  onClick={testCrypto}
                  className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
                >
                  Test Passphrase
                </button>
                
                {testResult && (
                  <div className="bg-gray-700 p-3 rounded-md text-sm">
                    <div className="mb-2"><strong>Passphrase:</strong> {testResult.passphrase}</div>
                    <div className="mb-2"><strong>Private Key:</strong> <span className="font-mono text-xs break-all">{testResult.private_key}</span></div>
                    <div className="mb-2"><strong>Address:</strong> <span className="font-mono text-xs">{testResult.bitcoin_address}</span></div>
                    <div><strong>Balance:</strong> <span className={testResult.balance > 0 ? "text-green-400" : "text-gray-400"}>{formatBalance(testResult.balance)}</span></div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Status Dashboard */}
          <div className="lg:col-span-2">
            {/* Current Status */}
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-bold mb-4 text-orange-400">Current Status</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-gray-700 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold">{status.total_attempts}</div>
                  <div className="text-sm text-gray-400">Session Attempts</div>
                </div>
                
                <div className="bg-gray-700 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-green-400">{status.found_keys}</div>
                  <div className="text-sm text-gray-400">Keys Found</div>
                </div>
                
                <div className="bg-gray-700 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold">{Math.round(status.progress)}</div>
                  <div className="text-sm text-gray-400">Attempts/Hour</div>
                </div>
                
                <div className="bg-gray-700 p-4 rounded-lg text-center">
                  <div className={`text-2xl font-bold ${status.is_running ? "text-green-400" : "text-red-400"}`}>
                    {status.is_running ? "RUNNING" : "STOPPED"}
                  </div>
                  <div className="text-sm text-gray-400">Status</div>
                </div>
              </div>
              
              {/* Overall Statistics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-gray-600 p-3 rounded-lg text-center">
                  <div className="text-lg font-bold text-blue-400">{stats.total_checked_passphrases}</div>
                  <div className="text-xs text-gray-400">Total Checked</div>
                </div>
                
                <div className="bg-gray-600 p-3 rounded-lg text-center">
                  <div className="text-lg font-bold text-yellow-400">{stats.total_attempts}</div>
                  <div className="text-xs text-gray-400">All-Time Attempts</div>
                </div>
                
                <div className="bg-gray-600 p-3 rounded-lg text-center">
                  <div className="text-lg font-bold text-green-400">{stats.total_successful_cracks}</div>
                  <div className="text-xs text-gray-400">Total Successes</div>
                </div>
                
                <div className="bg-gray-600 p-3 rounded-lg text-center">
                  <div className="text-lg font-bold text-purple-400">{stats.success_rate_percentage.toFixed(4)}%</div>
                  <div className="text-xs text-gray-400">Success Rate</div>
                </div>
              </div>
              
              {/* Progress Bar - now shows continuous operation */}
              <div className="bg-gray-700 rounded-full h-3 mb-4">
                <div
                  className={`h-3 rounded-full transition-all duration-500 ${
                    status.is_running ? "bg-green-500 animate-pulse" : "bg-gray-500"
                  }`}
                  style={{ width: status.is_running ? "100%" : "0%" }}
                ></div>
              </div>
              
              <div className="space-y-2 text-sm">
                <div><strong>Current Passphrase:</strong> <span className="font-mono text-orange-300">"{status.current_passphrase || "N/A"}"</span></div>
                <div><strong>Started:</strong> {formatTime(status.start_time)}</div>
                <div><strong>Mode:</strong> <span className="text-green-400">Continuous Operation (No Duplicates)</span></div>
              </div>
            </div>

            {/* Results Section */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              {/* Successful Cracks */}
              <div className="bg-gray-800 rounded-lg p-6">
                <h3 className="text-lg font-bold mb-4 text-green-400">🎯 Successful Cracks & Transfer Info</h3>
                
                {results.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">
                    No successful cracks yet...
                    <br />
                    <span className="text-sm">Bot is checking human-like passphrases continuously</span>
                  </div>
                ) : (
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {results.map((result, index) => (
                      <div key={index} className="bg-green-900/30 border border-green-700 p-4 rounded-lg">
                        <div className="flex justify-between items-center mb-3">
                          <div className="text-green-400 font-bold text-xl">💰 {formatBalance(result.balance)}</div>
                          <div className="text-xs text-gray-400">{formatTime(result.discovered_at)}</div>
                        </div>
                        
                        <div className="space-y-2 text-sm">
                          <div className="bg-gray-800 p-2 rounded">
                            <strong className="text-orange-400">Passphrase:</strong> 
                            <span className="font-mono ml-2 text-white">"{result.passphrase}"</span>
                          </div>
                          
                          <div className="bg-gray-800 p-2 rounded">
                            <strong className="text-blue-400">Bitcoin Address:</strong>
                            <div className="font-mono text-xs break-all text-white mt-1">{result.bitcoin_address}</div>
                          </div>
                          
                          <div className="bg-gray-800 p-2 rounded">
                            <strong className="text-purple-400">Private Key (Hex):</strong>
                            <div className="font-mono text-xs break-all text-white mt-1">{result.private_key}</div>
                          </div>
                          
                          {result.private_key_wif && (
                            <div className="bg-gray-800 p-2 rounded">
                              <strong className="text-yellow-400">Private Key (WIF):</strong>
                              <div className="font-mono text-xs break-all text-white mt-1">{result.private_key_wif}</div>
                            </div>
                          )}
                          
                          <div className="bg-red-900/30 border border-red-700 p-2 rounded">
                            <strong className="text-red-400">⚠️ Transfer Instructions:</strong>
                            <div className="text-xs text-gray-300 mt-1">
                              1. Import WIF key into Electrum, Bitcoin Core, or blockchain.info<br/>
                              2. Send funds to your secure wallet immediately<br/>
                              3. Keep this information private and secure
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent Attempts */}
              <div className="bg-gray-800 rounded-lg p-6">
                <h3 className="text-lg font-bold mb-4 text-blue-400">📝 Recent Attempts</h3>
                
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {recentAttempts.map((attempt, index) => (
                    <div key={index} className="bg-gray-700 p-3 rounded-lg text-sm">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-mono text-orange-300">{attempt.passphrase}</span>
                        <span className={attempt.balance > 0 ? "text-green-400" : "text-gray-500"}>
                          {formatBalance(attempt.balance)}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 font-mono break-all">
                        {attempt.bitcoin_address}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;