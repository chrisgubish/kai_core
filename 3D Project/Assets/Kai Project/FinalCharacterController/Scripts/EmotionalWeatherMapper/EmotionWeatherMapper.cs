using System.Collections;
using UnityEngine;
using UniStorm;
using EmotionResult = UnityJournalAPI.EmotionAnalysisResult;
using WeatherState = UnityJournalAPI.WeatherState;  // <-- use API's WeatherState

namespace KaiProject
{
    public class EmotionWeatherMapper : MonoBehaviour
    {
        #region Inspector Fields
        [Header("UniStorm Reference")]
        public UniStormSystem uniStormSystem;

        [Header("API Reference")]
        public UnityJournalAPI journalAPI;

        [Header("Weather Type Mappings")]
        public WeatherType clearWeather;
        public WeatherType mostlyClearWeather;
        public WeatherType partlyCloudyWeather;
        public WeatherType thunderWeather;
        public WeatherType foggyWeather;
        public WeatherType rainWeather;
        public WeatherType firestormWeather;

        [Header("Weather Mapping Configuration")]
        [Range(0f, 20f)] public float weatherTransitionSpeed = 3f;
        [Range(0f, 2f)]  public float intensityMultiplier   = 1.0f;

        [Header("Auto-Update Settings")]
        public bool  enableAutoUpdate = true;
        [Range(30f, 300f)]
        public float updateInterval   = 60f;

        [Header("Debug")] public bool enableDebugLogs = true;

        [Header("Current State (Read Only)")]
        [SerializeField] private string currentWeather  = "Clear";
        [SerializeField] private string currentEmotion  = "neutral";
        [SerializeField] private float  currentIntensity = 0.5f;
        #endregion

        #region Private Fields
        private Coroutine autoUpdateCoroutine;
        private bool isChangingWeather = false;
        #endregion

        #region Unity Lifecycle
        private void Start()
        {
            Debug.Log("[EmotionWeatherMapper] ===== INITIALIZATION STARTED =====");

            if (uniStormSystem == null)
            {
                uniStormSystem = FindObjectOfType<UniStormSystem>();
                if (uniStormSystem == null) { LogError("UniStorm System not found!"); return; }
                Debug.Log("[EmotionWeatherMapper] UniStorm System found successfully");
            }

            if (journalAPI == null)
            {
                journalAPI = FindObjectOfType<UnityJournalAPI>();
                if (journalAPI == null) { LogError("UnityJournalAPI not found!"); return; }
                Debug.Log("[EmotionWeatherMapper] UnityJournalAPI found successfully");
            }

            ValidateWeatherTypes();

            // Subscribe to emotion analysis events (journal submission)
            Debug.Log("[EmotionWeatherMapper] Subscribing to OnEmotionAnalyzed event...");
            journalAPI.OnEmotionAnalyzed += OnEmotionAnalyzed;
            Debug.Log("[EmotionWeatherMapper] Successfully subscribed to OnEmotionAnalyzed event!");

            if (enableAutoUpdate) StartAutoUpdate();

            Log("EmotionWeatherMapper initialized successfully");
            Debug.Log("[EmotionWeatherMapper] ===== INITIALIZATION COMPLETE =====");
        }

        private void OnDestroy()
        {
            if (journalAPI != null)
            {
                Debug.Log("[EmotionWeatherMapper] Unsubscribing from OnEmotionAnalyzed event");
                journalAPI.OnEmotionAnalyzed -= OnEmotionAnalyzed;
            }

            if (autoUpdateCoroutine != null) StopCoroutine(autoUpdateCoroutine);
        }

        private void ValidateWeatherTypes()
        {
            Debug.Log("[EmotionWeatherMapper] Validating weather type assignments...");
            if (clearWeather == null) LogWarning("Clear weather type not assigned!");                 else Debug.Log($"[EmotionWeatherMapper] Clear weather: {clearWeather.WeatherTypeName}");
            if (mostlyClearWeather == null) LogWarning("Mostly Clear weather type not assigned!");    else Debug.Log($"[EmotionWeatherMapper] Mostly Clear weather: {mostlyClearWeather.WeatherTypeName}");
            if (partlyCloudyWeather == null) LogWarning("Partly Cloudy weather type not assigned!");  else Debug.Log($"[EmotionWeatherMapper] Partly Cloudy weather: {partlyCloudyWeather.WeatherTypeName}");
            if (thunderWeather == null) LogWarning("Overcast weather type not assigned!");           else Debug.Log($"[EmotionWeatherMapper] Overcast weather: {thunderWeather.WeatherTypeName}");
            if (foggyWeather == null) LogWarning("Foggy weather type not assigned!");                 else Debug.Log($"[EmotionWeatherMapper] Foggy weather: {foggyWeather.WeatherTypeName}");
            if (rainWeather == null) LogWarning("Rain weather type not assigned!");                   else Debug.Log($"[EmotionWeatherMapper] Rain weather: {rainWeather.WeatherTypeName}");
            if (firestormWeather == null) LogWarning("Thunderstorm weather type not assigned!");   else Debug.Log($"[EmotionWeatherMapper] Thunderstorm weather: {firestormWeather.WeatherTypeName}");
        }
        #endregion

        #region Event Handlers (journal submission → emotion)
        private void OnEmotionAnalyzed(EmotionResult emotionData)
        {
            Debug.Log("[EmotionWeatherMapper] ===== EMOTION EVENT RECEIVED =====");
            Debug.Log($"[EmotionWeatherMapper] Primary Emotion: {emotionData.primary_emotion}");
            Debug.Log($"[EmotionWeatherMapper] Intensity: {emotionData.intensity}");
            Debug.Log($"[EmotionWeatherMapper] Confidence: {emotionData.confidence}");
            Debug.Log($"[EmotionWeatherMapper] Valence: {emotionData.valence}");
            Debug.Log($"[EmotionWeatherMapper] Arousal: {emotionData.arousal}");

            var weatherType = MapEmotionToWeatherType(emotionData.primary_emotion);
            if (weatherType != null)
            {
                float intensity = emotionData.intensity * intensityMultiplier;
                ChangeWeatherBasedOnEmotion(weatherType, intensity, emotionData.primary_emotion);
            }
            else
            {
                LogError($"No weather type assigned for emotion: {emotionData.primary_emotion}");
            }

            Debug.Log("[EmotionWeatherMapper] ===== EMOTION EVENT PROCESSING COMPLETE =====");
        }
        #endregion

        #region Weather Mapping
        private WeatherType MapEmotionToWeatherType(string emotion)
        {
            Debug.Log($"[EmotionWeatherMapper] Mapping emotion '{emotion}' to weather type...");
            WeatherType result;

            switch (emotion?.ToLower())
            {
                case "joy":      result = clearWeather;                              break;
                case "neutral":  result = mostlyClearWeather ?? clearWeather;        break;
                case "sadness":  result = rainWeather ?? thunderWeather;            break;
                case "anger":    result = firestormWeather ?? rainWeather;        break;
                case "fear":     result = foggyWeather ?? thunderWeather;           break;
                case "surprise": result = partlyCloudyWeather ?? mostlyClearWeather; break;
                case "disgust":  result = thunderWeather ?? partlyCloudyWeather;    break;
                default:         LogWarning($"Unknown emotion '{emotion}', using Clear"); result = clearWeather; break;
            }

            if (result == null) LogError($"Failed to map emotion '{emotion}' - result is null!");
            return result;
        }

        public void ChangeWeatherBasedOnEmotion(WeatherType weatherType, float intensity, string emotion)
        {
            if (isChangingWeather) { Log("Weather change already in progress, skipping..."); return; }
            if (uniStormSystem == null) { LogError("Cannot change weather - UniStorm System not assigned!"); return; }
            if (weatherType == null)    { LogError("Cannot change weather - WeatherType is null!"); return; }

            StartCoroutine(ChangeWeatherCoroutine(weatherType, intensity, emotion));
        }

        private IEnumerator ChangeWeatherCoroutine(WeatherType weatherType, float intensity, string emotion)
        {
            isChangingWeather = true;

            currentWeather  = weatherType.WeatherTypeName;
            currentEmotion  = emotion;
            currentIntensity = intensity;

            float transitionSpeed = Mathf.Lerp(weatherTransitionSpeed * 2f, weatherTransitionSpeed * 0.5f, intensity);

            try
            {
                uniStormSystem.TransitionSpeed = (int)transitionSpeed;
                Debug.Log($"[EmotionWeatherMapper] ===== CHANGING WEATHER =====");
                Debug.Log($"Target: {weatherType.WeatherTypeName}  Emotion: {emotion}  Intensity: {intensity:F2}  Speed: {transitionSpeed:F1}");
                uniStormSystem.ChangeWeather(weatherType);
            }
            catch (System.Exception e)
            {
                LogError($"Failed to change weather: {e.Message}\n{e.StackTrace}");
            }

            yield return new WaitForSeconds(2f);
            isChangingWeather = false;
            Debug.Log("[EmotionWeatherMapper] Weather change coroutine complete");
        }
        #endregion

        #region Auto-Update System (poll backend weather-state)
        public void StartAutoUpdate()
        {
            if (autoUpdateCoroutine != null) StopCoroutine(autoUpdateCoroutine);
            autoUpdateCoroutine = StartCoroutine(AutoUpdateCoroutine());
            Log($"Auto-update started (interval: {updateInterval}s)");
        }

        public void StopAutoUpdate()
        {
            if (autoUpdateCoroutine != null)
            {
                StopCoroutine(autoUpdateCoroutine);
                autoUpdateCoroutine = null;
                Log("Auto-update stopped");
            }
        }

        private IEnumerator AutoUpdateCoroutine()
        {
            yield return new WaitForSeconds(5f);
            while (true)
            {
                if (journalAPI != null && journalAPI.IsAuthenticated)
                {
                    Log("Requesting weather state update...");
                    journalAPI.GetWeatherState(OnWeatherStateReceived); // <-- correct signature now
                }
                yield return new WaitForSeconds(updateInterval);
            }
        }

        // receive UnityJournalAPI.WeatherState
        private void OnWeatherStateReceived(WeatherState state)
        {
            if (state == null) { LogWarning("Received null weather data"); return; }

            // state.weather_type (string), state.emotion (string), state.intensity (float)
            Log($"Weather state: {state.weather_type} (emotion: {state.emotion}, intensity: {state.intensity})");

            var weatherType = MapEmotionToWeatherType(state.emotion);
            if (weatherType != null)
            {
                ChangeWeatherBasedOnEmotion(weatherType, state.intensity, state.emotion);
            }
        }
        #endregion

        #region Manual Weather Control
        public void RequestWeatherUpdate()
        {
            if (journalAPI == null || !journalAPI.IsAuthenticated)
            {
                LogWarning("Cannot request weather - not authenticated");
                return;
            }
            Log("Manual weather update requested");
            journalAPI.GetWeatherState(OnWeatherStateReceived); // <-- correct signature
        }

        public void SetWeatherDirectly(WeatherType weatherType)
        {
            if (uniStormSystem == null) { LogError("Cannot set weather - UniStorm not assigned!"); return; }
            if (weatherType == null)    { LogError("Cannot set weather - WeatherType is null!"); return; }
            try { Log($"Directly setting weather to '{weatherType.WeatherTypeName}'"); uniStormSystem.ChangeWeather(weatherType); }
            catch (System.Exception e) { LogError($"Failed to set weather: {e.Message}"); }
        }
        #endregion

        #region Public Getters
        public string GetCurrentWeather()  => currentWeather;
        public string GetCurrentEmotion()  => currentEmotion;
        public float  GetCurrentIntensity()=> currentIntensity;
        public bool   IsAutoUpdateEnabled()=> enableAutoUpdate && autoUpdateCoroutine != null;
        #endregion

        #region Logging
        private void Log(string msg)       { if (enableDebugLogs) Debug.Log($"[EmotionWeatherMapper] {msg}"); }
        private void LogWarning(string msg) { Debug.LogWarning($"[EmotionWeatherMapper] WARNING: {msg}"); }
        private void LogError(string msg)   { Debug.LogError($"[EmotionWeatherMapper] ERROR: {msg}"); }
        #endregion
    }
}
