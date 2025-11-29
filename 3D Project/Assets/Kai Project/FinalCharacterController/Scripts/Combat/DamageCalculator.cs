using UnityEngine;

public class DamageCalculator : MonoBehaviour
{
    [SerializeField] EmotionCombatBridge emotion; // assign in Inspector

    public int ComputeDamage(int baseAttack, float baseCritChance, out bool crit){
        float atkMult   = emotion ? emotion.AttackMult : 1f;
        float critAdd   = emotion ? emotion.CritChanceAdd : 0f;

        float atk = baseAttack * atkMult;
        float chance = Mathf.Clamp01(baseCritChance + critAdd);

        crit = UnityEngine.Random.value < chance;
        if (crit) atk *= 1.5f; 

        return Mathf.Max(1, Mathf.RoundToInt(atk));
    }

    public int ComputeMitigated(int incoming, int baseDefense){
        float defMult = emotion ? emotion.DefenseMult : 1f;
        float def = baseDefense * defMult;

        float reduced = incoming - def; 
        return Mathf.Max(1, Mathf.RoundToInt(reduced));
    }
}
