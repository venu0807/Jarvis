# Runbook: Ollama Unavailable

## Overview
Ollama (local LLM server) becomes unreachable, affecting AI-powered features in automations (job classification, cover letter generation, resume tailoring, etc.).

## Symptoms
- "connection refused" or "timeout" errors when calling Ollama API
- AI-powered features return fallback responses or fail
- Logs show errors like "Failed to connect to Ollama at http://localhost:11434"
- Specific automation features affected:
  - Job classification/relevance scoring
  - Cover letter generation
  - Resume tailoring/optimization
  - Interview question prediction
  - Skill gap analysis
- Alert triggered: "Ollama unavailable"

## Impact
- Reduced automation effectiveness (reliance on rule-based fallbacks)
- Lower quality job matches and applications
- Generic cover letters instead of personalized ones
- Less effective resume tailoring
- Potential decrease in application success rates
- Increased manual workload for AI-dependent tasks

## Immediate Actions
1. **Check if Ollama service is running**:
   ```bash
   systemctl --user status ollama
   ```

2. **Check if Ollama is listening on port 11434**:
   ```bash
   ss -tlnp | grep 11434
   # or
   netstat -tlnp | grep 11434
   ```

3. **Attempt to connect to Ollama API directly**:
   ```bash
   curl http://localhost:11434/api/tags
   # Should return JSON with list of available models
   ```

4. **Check Ollama logs for errors**:
   ```bash
   journalctl --user -u ollama --since "1 hour ago"
   ```

5. **Restart Ollama service**:
   ```bash
   systemctl --user restart ollama
   ```

6. **Verify Ollama is working after restart**:
   ```bash
   curl http://localhost:11434/api/tags
   curl http://localhost:11434/api/show -d '{"name": "llama3.2"}'
   ```

## Common Causes & Solutions

### 1. Ollama Service Not Running
**Symptoms**: `Connection refused` on port 11434
**Solution**:
```bash
systemctl --user start ollama
systemctl --user enable ollama  # Start on login
```

### 2. Ollama Process Crashed or Hung
**Symptoms**: Service shows active but API doesn't respond
**Solution**:
```bash
systemctl --user stop ollama
# Wait a few seconds, then check if process is gone
ps aux | grep ollama
systemctl --user start ollama
```

### 3. Insufficient Resources (RAM/VRAM)
**Symptoms**: Ollama starts but becomes unresponsive when loading models
**Solution**:
- Check memory usage: `free -h` or `htop`
- Check if model is too large for available VRAM/RAM
- Try using a smaller model: `ollama run llama3.2:1b` instead of `llama3.2`
- Consider offloading to CPU: Set `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_MAX_LOADED_MODELS=1`
- Increase system swap space if needed

### 4. Model Not Available
**Symptoms**: API responds but model-specific calls fail with "model not found"
**Solution**:
- List available models: `ollama list`
- Pull the required model: `ollama pull llama3.2`
- Check model name spelling in automation code

### 5. Port Conflict
**Symptoms**: Ollama fails to start or another service is on port 11434
**Solution**:
- Check what's on port 11434: `ss -tlnp | grep 11434`
- If another service, stop it or change Ollama port
- To change Ollama port, set environment variable: `OLLAMA_HOST=0.0.0.0:11435` then restart

## Verification
1. Ollama service active: `systemctl --user is-active ollama`
2. API responsive: `curl -s http://localhost:11434/api/tags | jq .` returns valid JSON
3. Model available: `curl -s http://localhost:11434/api/show -d '{"name": "llama3.2"}' | jq .` returns model details
4. Automation AI features working:
   - Test job classification: Run a job through the pipeline and check logs for classification results
   - Test cover letter generation: Trigger cover letter creation and verify output quality
5. Alert triggers clear (no more Ollama unavailable alerts)

## Prevention
- Monitor Ollama memory usage: Set up alerts for high RAM consumption
- Keep Ollama updated: Regularly check for new versions
- Pre-load commonly used models during off-peak hours
- Monitor model loading times and set up performance alerts
- Consider implementing a simple health check endpoint for Ollama
- Document which models are used by which automations for quick reference

## Model Management
Ollama stores models in `~/.ollama/models/`. To manage disk space:

### List installed models:
```bash
ollama list
```

### Remove unused models:
```bash
ollama rm model_name
```

### Check model storage location and size:
```bash
du -sh ~/.ollama/models/
```

### Common models used in JARVIS:
- `llama3.2`: Primary model for text generation
- `llama3.2:1b`: Smaller/faster variant for simpler tasks
- `nomic-embed-text`: For embeddings (if used)
- `codellama`: For code-related tasks (if any)

## Troubleshooting Tips
1. **Check journalctl for detailed errors**:
   ```bash
   journalctl --user -u ollama -f  # Follow logs in real time
   ```

2. **Test with simple curl commands**:
   ```bash
   # List models
   curl http://localhost:11434/api/tags
   
   # Generate text (replace with your prompt)
   curl http://localhost:11434/api/generate -d '{
     "model": "llama3.2",
     "prompt": "Say hello in JSON format:",
     "stream": false
   }'
   
   # Get embeddings
   curl http://localhost:11434/api/embeddings -d '{
     "model": "nomic-embed-text",
     "prompt": "Sample text for embedding"
   }'
   ```

3. **Check automation-specific Ollama usage**:
   - Look for `OLLAMA_HOST` or `OLLAMA_MODEL` environment variables in automation configs
   - Check `shared_utils.py` or `shared_dom_llm.py` for Ollama client configuration
   - Verify timeout settings are appropriate for your model size

## References
- Ollama documentation: https://ollama.com/docs
- JARVIS AI integration: See `shared_utils.py` and `shared_dom_llm.py`
- Model library: https://ollama.com/library
- GPU acceleration: https://github.com/ollama/ollama#gpu-support