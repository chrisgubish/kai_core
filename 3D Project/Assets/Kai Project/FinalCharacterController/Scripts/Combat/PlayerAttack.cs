using UnityEngine;

public class PlayerAttack : MonoBehaviour
{
    [SerializeField] DamageCalculator calc;
    [SerializeField] int   baseAttack = 10;
    [SerializeField] float baseCritChance = 0.10f;
    [SerializeField] float hitRange = 3.0f;
    [SerializeField] LayerMask hitMask = ~0;  // default: everything
    [SerializeField] bool  debugLogs = true;
    [SerializeField] Transform projectileSpawnPoint;

    void Reset() { calc = GetComponent<DamageCalculator>(); }

    void Update()
    {
        if (Input.GetMouseButtonDown(0))
            PerformAttack();
    }

    void PerformAttack()
    {
        bool crit;
        int dmg = calc.ComputeDamage(baseAttack, baseCritChance, out crit);

        Camera cam = Camera.main;
        if (!cam) { if (debugLogs) Debug.LogWarning("No MainCamera."); return; }

        Ray ray = cam.ScreenPointToRay(new Vector3(Screen.width * 0.5f, Screen.height * 0.5f, 0));
        Debug.DrawRay(ray.origin, ray.direction * hitRange, Color.red, 0.25f);

        if (Physics.Raycast(ray, out RaycastHit hit, hitRange, hitMask))
        {
            var hp = hit.collider.GetComponentInParent<Health>();
            if (hp) hp.TakeDamage(dmg);
            else if (debugLogs) Debug.Log($"Hit {hit.collider.name} (no Health).");
        }
        else if (debugLogs) Debug.Log("No world hit.");

        if (debugLogs) Debug.Log($"Attack dealt {dmg} (crit={crit})");
    }
}
