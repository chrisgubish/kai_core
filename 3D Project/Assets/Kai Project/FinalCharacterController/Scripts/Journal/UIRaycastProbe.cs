using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

[RequireComponent(typeof(GraphicRaycaster))]
public class UIRaycastProbe : MonoBehaviour
{
    private GraphicRaycaster raycaster;
    private EventSystem es;

    void Awake()
    {
        raycaster = GetComponent<GraphicRaycaster>();
        es = EventSystem.current; // auto-picks the scene EventSystem
    }

    void Update()
    {
        if (Input.GetMouseButtonDown(0))
        {
            var ped = new PointerEventData(es) { position = Input.mousePosition };
            var results = new List<RaycastResult>();
            raycaster.Raycast(ped, results);

            if (results.Count > 0)
                Debug.Log("[UIRaycastProbe] Top hit: " + results[0].gameObject.name);
            else
                Debug.Log("[UIRaycastProbe] No UI hit.");
        }
    }
}
