# Research foundations for TCPS-PA v2.1

This file records method sources, not experimental evidence. Citing a paper never upgrades a run-level claim.

## 1. Bidirectional diagnosis and monitoring

- Antonante, Nilsen, and Carlone, *Monitoring of Perception Systems: Deterministic, Probabilistic, and Learning-based Fault Detection and Identification* (2022), formalizes diagnostic graphs, fault detection/identification, and diagnosability, with experiments on Apollo Auto: <https://arxiv.org/abs/2205.10906>.
- Leveson and Thomas, *STPA Handbook*, distinguishes proactive hazard/scenario analysis from causal analysis of observed loss and emphasizes unsafe control actions, feedback, and loss scenarios: <https://psas.scripts.mit.edu/home/get_file.php?name=STPA_handbook.pdf>.
- Leveson, *Engineering a Safer World*, treats safety as a system control problem and motivates analysis beyond linear component-failure chains: <https://doi.org/10.7551/mitpress/8179.001.0001>.
- Chhokra et al., *Towards Diagnosing Cascading Outages in Cyber Physical Energy Systems using Temporal Causal Models* (2017), uses temporal causal diagrams for cascading-failure diagnosis: <https://doi.org/10.36001/phmconf.2017.v9i1.2457>.
- DriveFI demonstrates systematic fault injection for end-to-end AV resilience testing, but injection evidence is not evidence of naturally occurring intrinsic defects: <https://research.nvidia.com/publication/2019-06_ml-based-fault-injection-autonomous-vehicles-case-bayesian-fault>.

TCPS-PA engineering consequence: preserve forward intervention confirmation while adding a separate abductive backward mode. Reverse edges generate candidates and discriminating tests; they do not invert causal implication.

## 2. Dynamic physical deadlines and safety envelopes

- Shalev-Shwartz, Shammah, and Shashua, *On a Formal Model of Safe and Scalable Self-driving Cars* (2017), provides the white-box RSS longitudinal safe-distance construction parameterized by response time, acceleration, and braking: <https://arxiv.org/abs/1708.06374>.
- Leung et al., *On Infusing Reachability-Based Safety Assurance within Planning Frameworks for Human-Robot Vehicle Interactions* (2020), uses reachability to preserve collision-free escape maneuvers under uncertain counterpart behavior: <https://arxiv.org/abs/2012.03390>.
- ISO 21448:2022 provides the SOTIF argument and validation context for performance insufficiencies in intended functionality; it does not supply experiment-specific numerical deadlines: <https://www.iso.org/standard/77490.html>.
- UNECE Regulation No. 157 provides an official ALKS regulatory context for following distance and collision avoidance, but its domain and assumptions must not be silently generalized: <https://unece.org/transport/documents/2021/03/standards/un-regulation-no-157-automated-lane-keeping-systems-alks>.

TCPS-PA engineering consequence: construct `tau_req(x)` only from pre-outcome state and independently qualified dynamics, publish uncertainty bounds, and keep legal, engineering, reconstructed, and model deadlines distinct.

## 3. Real-time deadlines and propagation

- Toba and Azumi, *Deadline Miss Early Detection Method for DAG Tasks Considering Variable Execution Time*, ECRTS 2024, models autonomous-driving sensor-to-control processing as mixed timer/event-driven DAG nodes and reasons from an end-to-end deadline under execution-time variation: <https://doi.org/10.4230/LIPIcs.ECRTS.2024.8>.

TCPS-PA engineering consequence: a physical end-to-end deadline and per-node computational budget are distinct artifacts. Backward diagnosis may use node-level timing to discriminate candidates, but must not replace the physical C4 requirement.

## 4. Clock uncertainty versus periodic phase

- RFC 5905 defines offset, delay, dispersion, jitter, precision, and synchronization distance for clock-quality assessment: <https://www.rfc-editor.org/info/rfc5905/>.
- IEEE 802.1AS specifies time synchronization for time-sensitive applications on bridged LANs and applies IEEE 1588 mechanisms: <https://www.ieee802.org/1/pages/802.1as.html>.
- CARLA's official synchrony/time-step documentation distinguishes client/server synchrony, fixed/variable time steps, substepping, determinism, and tick progression: <https://carla.readthedocs.io/en/latest/adv_synchrony_timestep/>.

TCPS-PA engineering consequence: `P_CLOCK` evaluates whether timestamps can be compared within an error budget. `P_PHASE` evaluates whether sampling/timer/tick alignment changes observed latency or outcome. Neither is a proxy for the other.

## 5. Validator recomputation

The L5 recomputation rule is an evidence-integrity control derived from numerical traceability rather than a claim that a specific paper mandates the exact CSV schema. It applies the established wall-clock trapezoidal integral directly to observed velocity samples and checks arithmetic ancestry:

`D_response = integral(t1,t_e,v(t)dt_wall)`

`D_debt = max(0, integral(t1+tau_req,t_e,v(t)dt_wall))`

`M0 = D1 - D_response - D_brake`

This prevents an evidence label from laundering an incompatible clock, endpoint, model value, or fabricated scalar into C5.
