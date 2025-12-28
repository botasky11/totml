import type { WebSocketMessage } from '@/types';

type MessageHandler = (message: WebSocketMessage) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private handlers: Set<MessageHandler> = new Set();
  private shouldReconnect = true; // 标志：是否应该重连
  private connectTimeout: number | null = null;

  constructor(private experimentId: string) {
    console.log(`[WS_CLIENT] WebSocketService created for experiment: ${experimentId}`);
  }

  connect() {
    // 如果已经有连接，先清理
    if (this.ws) {
      console.log(`[WS_CLIENT] Closing existing connection before reconnect`);
      this.ws.close();
      this.ws = null;
    }

    const wsUrl = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000';
    const url = `${wsUrl}/api/v1/experiments/ws/${this.experimentId}`;

    console.log(`[WS_CLIENT] Attempting to connect to: ${url}`);
    console.log(`[WS_CLIENT] Environment VITE_WS_URL: ${(import.meta as any).env?.VITE_WS_URL}`);

    // 重置重连标志（允许自动重连）
    this.shouldReconnect = true;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log(`[WS_CLIENT] ✅ WebSocket connected successfully for experiment ${this.experimentId}`);
      console.log(`[WS_CLIENT] Connection time: ${new Date().toISOString()}`);
      console.log(`[WS_CLIENT] ReadyState: ${this.ws?.readyState} (OPEN = 1)`);
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      console.log(`[WS_CLIENT] 📨 Received message for experiment ${this.experimentId}:`, event.data);
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        console.log(`[WS_CLIENT] Parsed message type: ${message.type}`);
        console.log(`[WS_CLIENT] Message data:`, message.data);
        console.log(`[WS_CLIENT] Active handlers count: ${this.handlers.size}`);

        let handlerIndex = 0;
        this.handlers.forEach((handler) => {
          handlerIndex++;
          console.log(`[WS_CLIENT] Calling handler #${handlerIndex}`);
          handler(message);
        });

        console.log(`[WS_CLIENT] All handlers executed successfully`);
      } catch (error) {
        console.error(`[WS_CLIENT] ❌ Failed to parse WebSocket message:`, error);
        console.error(`[WS_CLIENT] Raw data:`, event.data);
      }
    };

    this.ws.onerror = () => {
      const readyState = this.ws?.readyState;

      // 友好的错误处理，区分不同场景
      if (readyState === WebSocket.CONNECTING || readyState === undefined) {
        console.log(`[WS_CLIENT] ⚠️ Connection interrupted during handshake (likely React Strict Mode in dev)`);
      } else if (readyState === WebSocket.OPEN) {
        console.error(`[WS_CLIENT] ❌ WebSocket error during active connection for experiment ${this.experimentId}`);
      } else {
        console.warn(`[WS_CLIENT] WebSocket error in state ${readyState} for experiment ${this.experimentId}`);
      }
    };

    this.ws.onclose = (event) => {
      console.log(`[WS_CLIENT] WebSocket closed for experiment ${this.experimentId}`);
      console.log(`[WS_CLIENT] Close code: ${event.code}, reason: ${event.reason}`);
      console.log(`[WS_CLIENT] Was clean: ${event.wasClean}`);
      console.log(`[WS_CLIENT] Should reconnect: ${this.shouldReconnect}`);

      // 只在需要重连时才尝试重连（排除主动关闭的情况）
      if (this.shouldReconnect) {
        this.attemptReconnect();
      } else {
        console.log(`[WS_CLIENT] ⏹️ Connection closed intentionally, not reconnecting`);
      }
    };
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * this.reconnectAttempts;

      // 如果是第一次重连，可能是开发环境的Strict Mode导致的，日志友好一些
      if (this.reconnectAttempts === 1) {
        console.log(`[WS_CLIENT] 🔄 Reconnecting... (1/${this.maxReconnectAttempts})`);
      } else {
        console.log(`[WS_CLIENT] 🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        console.log(`[WS_CLIENT] Reconnect delay: ${delay}ms`);
      }

      setTimeout(() => {
        if (this.shouldReconnect) {
          console.log(`[WS_CLIENT] Executing reconnect attempt #${this.reconnectAttempts}`);
          this.connect();
        } else {
          console.log(`[WS_CLIENT] ⏹️ Reconnection cancelled (disconnect was called)`);
        }
      }, delay);
    } else {
      console.error(`[WS_CLIENT] ❌ Max reconnection attempts (${this.maxReconnectAttempts}) reached for experiment ${this.experimentId}`);
    }
  }

  subscribe(handler: MessageHandler) {
    console.log(`[WS_CLIENT] Adding message handler for experiment ${this.experimentId}`);
    console.log(`[WS_CLIENT] Total handlers before add: ${this.handlers.size}`);
    this.handlers.add(handler);
    console.log(`[WS_CLIENT] Total handlers after add: ${this.handlers.size}`);
    return () => {
      console.log(`[WS_CLIENT] Removing message handler for experiment ${this.experimentId}`);
      this.handlers.delete(handler);
    };
  }

  disconnect() {
    console.log(`[WS_CLIENT] Disconnecting WebSocket for experiment ${this.experimentId}`);

    // 设置标志：不应该重连（这是主动关闭）
    this.shouldReconnect = false;

    // 清除任何待处理的连接超时
    if (this.connectTimeout !== null) {
      clearTimeout(this.connectTimeout);
      this.connectTimeout = null;
    }

    if (this.ws) {
      const state = this.ws.readyState;
      console.log(`[WS_CLIENT] Closing WebSocket connection, current state: ${state} (${this.getStateName(state)})`);

      // 只在OPEN或CLOSING状态时关闭，避免在CONNECTING状态下关闭导致警告
      if (state === WebSocket.OPEN || state === WebSocket.CLOSING) {
        this.ws.close();
      } else if (state === WebSocket.CONNECTING) {
        console.log(`[WS_CLIENT] ⏳ Connection still establishing, waiting for onopen/onerror to close`);
        // 在CONNECTING状态下，设置一个标志让onopen/onerror处理关闭
        const tempWs = this.ws;
        // const originalOnOpen = this.ws.onopen;
        const originalOnError = this.ws.onerror;

        this.ws.onopen = () => {
          console.log(`[WS_CLIENT] Connection opened during disconnect, closing immediately`);
          if (tempWs.readyState === WebSocket.OPEN) {
            tempWs.close();
          }
        };

        this.ws.onerror = (error) => {
          console.log(`[WS_CLIENT] Connection failed during disconnect, ignoring`);
          // 调用原始错误处理（如果需要）
          if (originalOnError) {
            originalOnError.call(tempWs, error);
          }
        };
      }
      this.ws = null;
    }
    console.log(`[WS_CLIENT] Clearing ${this.handlers.size} handlers`);
    this.handlers.clear();
  }

  private getStateName(state: number): string {
    switch (state) {
      case WebSocket.CONNECTING: return 'CONNECTING';
      case WebSocket.OPEN: return 'OPEN';
      case WebSocket.CLOSING: return 'CLOSING';
      case WebSocket.CLOSED: return 'CLOSED';
      default: return 'UNKNOWN';
    }
  }

  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log(`[WS_CLIENT] Sending message to server:`, message);
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn(`[WS_CLIENT] Cannot send message, WebSocket is not open. ReadyState: ${this.ws?.readyState}`);
    }
  }
}
