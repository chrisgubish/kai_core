using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;

public class PauseMenuController : MonoBehaviour
{
    [Header("UI")]
    [SerializeField] private GameObject pausePanel;           // root panel to show/hide
    [SerializeField] private GameObject firstSelected;        // optional: first selectable for gamepad

    [Header("Input")]
    [SerializeField] private InputActionReference pauseAction; // PlayerActionMap/Pause

    private InputAction _pause;

    private bool _isPaused;

    private void OnEnable()
    {
        if (pauseAction != null && pauseAction.action != null)
        {
            _pause = pauseAction.action;
            _pause.actionMap?.Enable();
            if (!_pause.enabled) _pause.Enable();
            _pause.performed += OnPausePerformed;
        }
    }

    private void OnDisable()
    {
        if (_pause != null)
            _pause.performed -= OnPausePerformed;

        // Safety: always restore timescale if this component is disabled while paused
        if (_isPaused) SetPaused(false);
    }

    private void OnPausePerformed(InputAction.CallbackContext ctx)
    {
        SetPaused(!_isPaused);
    }

    private void SetPaused(bool paused)
    {
        _isPaused = paused;

        // UI
        if (pausePanel) pausePanel.SetActive(paused);

        // Time
        Time.timeScale = paused ? 0f : 1f;

        // Cursor
        Cursor.visible = paused;
        Cursor.lockState = paused ? CursorLockMode.None : CursorLockMode.Locked;

        // Gamepad focus (optional)
        if (paused && firstSelected != null && EventSystem.current != null)
            EventSystem.current.SetSelectedGameObject(firstSelected);
    }

    // Public button hooks (optional)
    public void Resume() => SetPaused(false);
    public void QuitToMainMenu() { /* load scene, cleanup, etc. */ }
}
