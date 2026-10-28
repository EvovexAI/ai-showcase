import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI Video Decompose - 视频拆解',
  description: '抖音视频一键分析，提取关键帧、口播脚本',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        {children}
      </body>
    </html>
  );
}
