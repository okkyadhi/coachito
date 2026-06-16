// Static skill-level descriptors.  Mirrors apps/api/data/descriptors_padel.json
// — these are platform-locked, never change, ~25 KB before gzip.  When BE
// step 12 ships `GET /skills/:code/descriptors`, replace this with a cached
// API fetch in TanStack Query.

import type { SkillCategory } from '@/features/trainee-profile/profile-types';

export interface SkillDescriptors {
  skillCode: string;
  category: SkillCategory;
  nameEn: string;
  descriptions: [string, string, string, string, string]; // levels 1-5
}

const D = (
  skillCode: string,
  category: SkillCategory,
  nameEn: string,
  d: [string, string, string, string, string],
): SkillDescriptors => ({ skillCode, category, nameEn, descriptions: d });

export const SKILL_DESCRIPTORS: SkillDescriptors[] = [
  D('PADEL_TECH_FH', 'technical', 'Forehand Drive', [
    'Inconsistent contact, ball flies erratically, no swing structure',
    'Makes contact ~6/10 in cooperative rally, no direction control, often into net',
    'Consistent crosscourt rally at moderate pace, basic depth control',
    'Controls direction & depth in match play, attacks short balls aggressively',
    'Weapon shot — varies pace, spin, depth, direction at will under pressure',
  ]),
  D('PADEL_TECH_BH', 'technical', 'Backhand Drive', [
    'Uses forehand grip, weak block contact, can’t drive',
    'Switches grip but inconsistent contact, often hits with frame',
    'Consistent block backhand crosscourt, limited topspin',
    'Reliable in match play, drives backhand with depth, basic topspin',
    'Aggressive backhand with topspin, attacks down the line under pressure',
  ]),
  D('PADEL_TECH_FH_VOLLEY', 'technical', 'Forehand Volley', [
    'Swings at the ball, frame contacts common, often pops up',
    'Makes contact but no placement, short of net or floats',
    'Consistent block volley, keeps ball low, basic placement',
    'Controls direction with cut, can attack or defend based on situation',
    'Penetrating volley with cut & placement, dictates points from net',
  ]),
  D('PADEL_TECH_BH_VOLLEY', 'technical', 'Backhand Volley', [
    'Misses contact frequently, no grip change',
    'Block contact but ball lacks pace, pops up',
    'Consistent block backhand volley, keeps ball low',
    'Controls direction, absorbs pace and redirects',
    'Aggressive backhand volley with cut, attacks confidently',
  ]),
  D('PADEL_TECH_SERVE', 'technical', 'Serve', [
    'Inconsistent toss, double faults common, no direction control',
    'Gets serve in ~6/10, no placement, slow pace',
    'Consistent serve in service box, can target T or wide occasionally',
    'Reliable placement, varies pace, uses slice',
    'Strategic serve — varies placement, pace, spin to set up next shot',
  ]),
  D('PADEL_TECH_RETURN', 'technical', 'Return of Serve', [
    'Often misses, gets aced or returns short to opponent’s volley',
    'Returns over net but no placement, often goes to opponent’s volley',
    'Consistent return cross-court, keeps ball low, neutralizes serve',
    'Returns with intent — can lob, chip, or drive based on serve quality',
    'Uses return as offensive weapon, attacks weak serves consistently',
  ]),
  D('PADEL_TECH_LOB', 'technical', 'Defensive Lob (Globo)', [
    'Lobs too short or too long, often gets smashed',
    'Inconsistent height & depth, gets smashed or hits out',
    'Consistent depth & height, neutralizes opponent’s net pressure',
    'Tactical lobs — varies depth & spin, sets up own counter-attack',
    'Lob is a weapon — perfect height & depth, mixes in offensive lobs',
  ]),
  D('PADEL_TECH_BANDEJA', 'technical', 'Bandeja', [
    'Doesn’t recognize when to use it; uses smash or lets ball drop',
    'Recognizes opportunity but inconsistent contact, often into net',
    'Consistent contact with control, keeps ball deep, but loses net position often',
    'Controls direction & depth, maintains net position, slows opponents down',
    'Tactical bandeja — varies pace, spin, direction; offensive when needed',
  ]),
  D('PADEL_TECH_VIBORA', 'technical', 'Víbora', [
    'Confuses with bandeja, inconsistent contact, often goes long',
    'Recognizes when to use but contact inconsistent',
    'Consistent contact with side spin, keeps ball in',
    'Controls direction & spin, ball jumps out of court (good víbora)',
    'Devastating víbora — angles, spin, pace; finishes points consistently',
  ]),
  D('PADEL_TECH_SMASH', 'technical', 'Smash (Remate)', [
    'Times poorly, often misses, hits net or out',
    'Inconsistent timing, lacks power, opponent defends easily',
    'Consistent smash on easy balls, basic power & direction',
    'Powerful smash with placement, attacks defensive lobs effectively',
    'Devastating smash — uses kick, flat, angles; finishes points off any lob',
  ]),
  D('PADEL_TECH_WALL_BACK', 'technical', 'Back Wall Exit', [
    'Doesn’t read ball off back wall, late or rushed',
    'Reads ball but contact inconsistent, often hits weak return',
    'Reads back wall well, returns ball to neutral position',
    'Uses back wall to attack — sets up offensive shots from defense',
    'Master of back wall — can chiquita, lob, or drive based on opportunity',
  ]),
  D('PADEL_TECH_WALL_SIDE', 'technical', 'Side Wall Play', [
    'Confused by side wall, often misses ball or contacts late',
    'Reads side wall but rushed, returns weakly',
    'Reads side wall consistently, returns ball to neutral',
    'Uses side wall to attack — sets up counter from corner shots',
    'Comfortable with all wall combinations (back + side), creates winners',
  ]),
  D('PADEL_TECH_DROP', 'technical', 'Chiquita / Drop Shot', [
    'Drops too high or no spin, easy attack for opponent',
    'Inconsistent drop — sometimes too short, often too high',
    'Consistent low drop, opponent has to move forward to retrieve',
    'Tactical use — recognizes good moments, varies placement',
    'Drop is a weapon — surprises opponents, sets up traps',
  ]),
  D('PADEL_TACT_NET_POS', 'tactical', 'Net Positioning (Offensive)', [
    'Stands behind service line, gets lobbed easily, no awareness',
    'Stays at net but loses position after first volley, doesn’t recover',
    'Holds net in steady rallies, loses position under sustained pressure',
    'Maintains aggressive net position, recovers after bandeja, partners coordinate',
    'Dominates net consistently, dictates points, perfect positioning vs all opponents',
  ]),
  D('PADEL_TACT_DEF_POS', 'tactical', 'Defensive Positioning', [
    'Stays at baseline reactively, no court coverage awareness',
    'Knows to retreat when lobbed but slow recovery, gaps with partner',
    'Defends consistently, covers most of court with partner',
    'Active defense — sets up counter-attack, communicates with partner',
    'Defensive maestro — turns defense to offense reliably, never out of position',
  ]),
  D('PADEL_TACT_SHOT_SEL', 'tactical', 'Shot Selection', [
    'Hits whatever shot first comes to mind, often wrong choice',
    'Recognizes "easy" shots but unsure on tough decisions',
    'Reasonable shot choices in routine situations',
    'Smart shot selection — chooses based on opponent position, score, momentum',
    'Strategic mastermind — every shot has purpose, sets up patterns 2–3 shots ahead',
  ]),
  D('PADEL_TACT_PARTNER', 'tactical', 'Partner Coordination', [
    'No communication, plays as if alone on court',
    'Basic communication ("mine!", "out!") but no strategic talk',
    'Communicates routinely, switches when needed',
    'Coordinates strategy, plans points together, supports partner emotionally',
    'Synchronized play — telepathic positioning, consistent partnership',
  ]),
  D('PADEL_TACT_TRANSITION', 'tactical', 'Transition Play', [
    'Stays at baseline even when chance to attack, or rushes net poorly',
    'Recognizes when to come up but timing poor, gets caught in transition',
    'Comes to net at appropriate times, basic transition execution',
    'Smooth transition — uses bandeja/lob to set up net, recovers if pushed back',
    'Master of transition — flips defense to offense seamlessly, controls tempo',
  ]),
  D('PADEL_TACT_READING', 'tactical', 'Reading the Game', [
    'Reactive only, doesn’t anticipate opponent’s shots',
    'Reads obvious patterns but slow to adapt',
    'Anticipates routine situations, makes decent guesses',
    'Reads opponent well, anticipates shots based on position & body language',
    'Elite anticipation — reads serve placement, set-ups, knows next shot before opponent hits',
  ]),
  D('PADEL_PHYS_FOOTWORK', 'physical', 'Footwork & Court Coverage', [
    'Slow, flat-footed, often arrives too late or off-balance',
    'Improving movement but inefficient, takes wrong steps',
    'Consistent split step & basic court coverage, occasional inefficiency',
    'Efficient movement, cross-step & shuffle, balanced contact',
    'Elite footwork — anticipates, recovers fast, always in balance',
  ]),
  D('PADEL_PHYS_SPLIT', 'physical', 'Split Step & Reaction', [
    'No split step, flat-footed, late reactions',
    'Inconsistent split step, sometimes too early or late',
    'Consistent split step on opponent’s contact, decent reactions',
    'Reliable split + first-step explosiveness in match play',
    'Elite reactions — perfect timing, explosive first step, dominates short balls',
  ]),
  D('PADEL_PHYS_ENDURANCE', 'physical', 'Endurance', [
    'Tired after 30 minutes, can’t sustain quality in long rallies',
    'Lasts a set but quality drops in second set',
    'Plays 2 full sets at same level, tires in third',
    'Sustains quality across 3 sets, occasional fatigue late',
    'Tournament-ready endurance, maintains intensity in long matches & multi-day events',
  ]),
  D('PADEL_PHYS_POWER', 'physical', 'Power & Explosiveness', [
    'Lacks pace on shots, slow movement',
    'Decent power on easy balls, breaks down under pressure',
    'Solid power on groundstrokes, average on overheads',
    'Powerful shots & explosive movement, can finish points',
    'Elite power — generates pace from any position, dominates physically',
  ]),
  D('PADEL_MENT_FOCUS', 'mental', 'Focus & Concentration', [
    'Loses focus quickly, distracted easily, mistakes after errors',
    'Focused in spurts but drops off when behind or tired',
    'Maintains focus in routine matches, struggles in long sessions',
    'Stays focused in close matches, recovers quickly after distractions',
    'Laser focus — present every point, locked in for entire match',
  ]),
  D('PADEL_MENT_COMPOSURE', 'mental', 'Composure Under Pressure', [
    'Visibly affected by errors, body language drops, plays worse when behind',
    'Recovers slowly after mistakes, plays safer when behind',
    'Maintains form in routine pressure, struggles in tight scores',
    'Performs well in close sets, makes smart choices at 5–5',
    'Thrives in pressure — raises level when match is on the line',
  ]),
  D('PADEL_MENT_DECISION', 'mental', 'Decision-Making Speed', [
    'Slow decisions, hesitates, often hits wrong shot',
    'Improving but still slow on tough decisions',
    'Reasonable decisions in routine situations',
    'Quick & accurate decisions in match play, rarely wrong shot',
    'Lightning decisions — pattern recognition, intuitive shot selection',
  ]),
  D('PADEL_MENT_RESILIENCE', 'mental', 'Resilience After Errors', [
    'Errors compound — one mistake leads to several more',
    'Slow to recover from errors, lingering frustration',
    'Recovers within 1–2 points after mistakes',
    'Bounces back immediately, uses errors as feedback',
    'Unshakeable — plays better after adversity, mental warrior',
  ]),
];

const _BY_CODE: Record<string, SkillDescriptors> = Object.fromEntries(
  SKILL_DESCRIPTORS.map((d) => [d.skillCode, d]),
);

export function getDescriptors(skillCode: string): SkillDescriptors | undefined {
  return _BY_CODE[skillCode];
}

export function skillsByCategory(category: SkillCategory): SkillDescriptors[] {
  return SKILL_DESCRIPTORS.filter((d) => d.category === category);
}
