import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useCheckAndReport, useFitReports } from '@/api/hooks';
import type { FitReport } from '@/api/schema';
import { Button } from '@/components/Button';
import { Card, EmptyState, ErrorNotice } from '@/components/Card';
import { ConfidenceBadge } from '@/components/Chips';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { productDisplayName } from '@/fit/format';
import { spacing, typography } from '@/theme';

export default function CheckScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ url?: string }>();
  const [url, setUrl] = useState('');
  const reports = useFitReports();
  const check = useCheckAndReport();
  const handled = useRef<string | null>(null);

  const run = async (target: string) => {
    const trimmed = target.trim();
    if (!/^https?:\/\//i.test(trimmed)) return;
    const report = await check.mutateAsync({ url: trimmed, garment_kind: 'tee', refresh: false });
    setUrl('');
    router.push({ pathname: '/check/[reportId]', params: { reportId: report.id } });
  };

  // Share-sheet intake: the root layout routes here with ?url=
  useEffect(() => {
    if (params.url && handled.current !== params.url) {
      handled.current = params.url;
      setUrl(params.url);
      run(params.url).catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.url]);

  return (
    <Screen>
      <Text style={typography.heading}>Check a product</Text>
      <Text style={typography.caption}>
        Paste a product link, or share one from Safari with the share sheet and pick style.id.
      </Text>
      <TextField
        placeholder="https://shop.example.com/tee"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        value={url}
        onChangeText={setUrl}
        onSubmitEditing={() => run(url)}
      />
      <Button title="Check fit" loading={check.isPending} disabled={!/^https?:\/\//i.test(url.trim())} onPress={() => run(url)} />
      <ErrorNotice error={check.error} />

      <Text style={[typography.heading, { marginTop: spacing.lg }]}>Past reports</Text>
      <ErrorNotice error={reports.error} />
      {reports.data?.length === 0 ? (
        <EmptyState title="Nothing checked yet" body="Your fit reports will show up here." />
      ) : null}
      {reports.data?.map((r) => (
        <ReportCard key={r.id} report={r} onPress={() => router.push({ pathname: '/check/[reportId]', params: { reportId: r.id } })} />
      ))}
    </Screen>
  );
}

function ReportCard({ report, onPress }: { report: FitReport; onPress: () => void }) {
  const title = productDisplayName(report.product);
  return (
    <Card onPress={onPress}>
      <Text style={typography.body} numberOfLines={2}>
        {title}
      </Text>
      <View style={styles.row}>
        <Text style={typography.caption}>
          {report.report.pick ? `Pick: ${report.report.pick.size_label}` : 'No size fits'}
          {report.report.runner_up ? ` · then ${report.report.runner_up.size_label}` : ''}
        </Text>
        <ConfidenceBadge confidence={report.report.overall_confidence} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm, flexWrap: 'wrap' },
});
