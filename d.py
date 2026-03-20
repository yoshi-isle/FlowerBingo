bottleneck


values = np.unique(features[:, col])
for i in range(len(values) - 1):   # hundreds/thousands of thresholds per feature


With continuous data, that's thousands of candidate splits × every feature × every node × 80 trees. Replace that exhaustive scan with quantile-based candidate thresholds. This is the single change that matters:


for col in range(features.shape[1]):
    vals = features[:, col]

    # Only test ~10 candidate thresholds instead of every unique midpoint
    percentiles = np.percentile(vals, np.linspace(10, 90, 9))
    thresholds = np.unique(percentiles)

    for threshold in thresholds:
        go_left = vals <= threshold
        go_right = ~go_left

        if np.sum(go_left) < 2 or np.sum(go_right) < 2:
            continue

        gain = gini_gain(classes, [classes[go_left], classes[go_right]])
        if gain > best_gain:
            best_gain = gain
            best_feature = col
            best_threshold = threshold



That reduces the inner loop from potentially thousands of iterations to 9 per feature. On 80 trees with depth 5, that's the difference between 700 seconds and ~5-15 seconds.

If you want even more speed, add a minimum-samples guard at the top of __build_tree__:


if len(classes) < 5:
    values, ctns = np.unique(classes, return_counts=True)
    return DecisionNode(None, None, None, values[np.argmax(ctns)])


This prevents deep recursion on tiny leaf nodes. But the quantile fix alone should be sufficient to pass the benchmarks with good accuracy.